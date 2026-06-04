import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models import Source, DocumentText, SourceTag, Tag, Finding, Note
from app.schemas import SourceRead, SourceDetail, FindingCreate, FindingRead, NoteCreate, NoteRead, TagCreate
from app.services.pdf_service import extract_text_from_pdf, extract_metadata_from_pdf
from app.config import settings

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("/upload", response_model=SourceRead)
async def upload_source(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Nur PDF-Dateien erlaubt")

    content = await file.read()

    try:
        pages = extract_text_from_pdf(content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    upload_path = os.path.join(settings.upload_dir, safe_name)
    os.makedirs(settings.upload_dir, exist_ok=True)

    with open(upload_path, "wb") as f:
        f.write(content)

    meta = extract_metadata_from_pdf(content)
    title = meta["title"] or file.filename.removesuffix(".pdf")

    source = Source(
        title=title,
        authors=meta["authors"],
        year=meta["year"],
        doi=meta["doi"],
        journal=meta["journal"],
        filename=file.filename,
        file_path=upload_path,
    )
    db.add(source)
    db.flush()

    for page in pages:
        db.add(DocumentText(source_id=source.id, page_number=page["page_number"], text=page["text"]))

    db.commit()
    db.refresh(source)
    return _source_to_read(source)


@router.get("", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.created_at.desc()).all()
    return [_source_to_read(s) for s in sources]


@router.get("/{source_id}", response_model=SourceDetail)
def get_source(source_id: int, db: Session = Depends(get_db)):
    source = (
        db.query(Source)
        .options(
            selectinload(Source.texts),
            selectinload(Source.summaries),
            selectinload(Source.findings),
            selectinload(Source.notes),
            selectinload(Source.source_tags).selectinload(SourceTag.tag),
        )
        .filter(Source.id == source_id)
        .first()
    )
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")
    return _source_to_detail(source)


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")
    if os.path.exists(source.file_path):
        os.remove(source.file_path)
    db.delete(source)
    db.commit()
    return {"ok": True}


@router.post("/{source_id}/tags")
def add_tag(source_id: int, body: TagCreate, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")
    tag = db.query(Tag).filter(Tag.name == body.name).first()
    if not tag:
        tag = Tag(name=body.name)
        db.add(tag)
        db.flush()
    existing = db.query(SourceTag).filter_by(source_id=source_id, tag_id=tag.id).first()
    if not existing:
        db.add(SourceTag(source_id=source_id, tag_id=tag.id))
    db.commit()
    return {"ok": True}


@router.post("/{source_id}/findings", response_model=FindingRead)
def add_finding(source_id: int, body: FindingCreate, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")
    finding = Finding(source_id=source_id, **body.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


@router.post("/{source_id}/notes", response_model=NoteRead)
def add_note(source_id: int, body: NoteCreate, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")
    note = Note(source_id=source_id, **body.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def _source_to_read(source: Source) -> SourceRead:
    tags = [st.tag.name for st in source.source_tags]
    return SourceRead(
        id=source.id,
        title=source.title,
        authors=source.authors or "",
        year=source.year,
        doi=source.doi or "",
        journal=source.journal or "",
        filename=source.filename,
        created_at=source.created_at,
        tags=tags,
    )


def _source_to_detail(source: Source) -> SourceDetail:
    read = _source_to_read(source)
    return SourceDetail(
        **read.model_dump(),
        texts=[{"id": t.id, "page_number": t.page_number, "text": t.text} for t in source.texts],
        summaries=[{
            "id": s.id, "model_name": s.model_name, "prompt_version": s.prompt_version,
            "research_question": s.research_question, "methods": s.methods,
            "data_basis": s.data_basis, "key_results": s.key_results,
            "limitations": s.limitations, "relevance": s.relevance,
            "uncertainty_notes": s.uncertainty_notes, "created_at": s.created_at,
        } for s in source.summaries],
        findings=[{
            "id": f.id, "claim": f.claim, "evidence_text": f.evidence_text or "",
            "page_number": f.page_number, "relevance": f.relevance or "",
            "confidence": f.confidence, "created_at": f.created_at,
        } for f in source.findings],
        notes=[{
            "id": n.id, "text": n.text, "linked_page_number": n.linked_page_number,
            "linked_quote": n.linked_quote or "", "created_at": n.created_at,
        } for n in source.notes],
    )
