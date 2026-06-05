from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import ResearchArea, Finding, FindingResearchArea, SourceTag
from app.schemas import (
    ResearchAreaCreate, ResearchAreaRead, ResearchAreaUpdate,
    FindingAssignCreate, FindingAssignUpdate, ResearchAreaFindingEntry,
)

router = APIRouter(prefix="/api/research-areas", tags=["research-areas"])


def _get_area_or_404(area_id: int, db: Session) -> ResearchArea:
    area = db.get(ResearchArea, area_id)
    if not area:
        raise HTTPException(404, "ResearchArea nicht gefunden")
    return area


def _load_links(area_id: int, db: Session, filters: dict) -> list:
    q = (
        db.query(FindingResearchArea)
        .join(Finding)
        .filter(FindingResearchArea.research_area_id == area_id)
        .options(
            joinedload(FindingResearchArea.finding).joinedload(Finding.source),
        )
    )
    if not filters.get("include_unreviewed", True):
        q = q.filter(Finding.review_status != "unreviewed")
    if filters.get("review_status"):
        q = q.filter(Finding.review_status == filters["review_status"])
    if filters.get("validation_status"):
        q = q.filter(Finding.validation_status == filters["validation_status"])
    if filters.get("relation_type"):
        q = q.filter(FindingResearchArea.relation_type == filters["relation_type"])
    if filters.get("relevance"):
        q = q.filter(FindingResearchArea.relevance == filters["relevance"])
    links = q.all()
    # eagerly access source_tags and summaries while session is open
    for link in links:
        _ = [st.tag.name for st in link.finding.source.source_tags]
        _ = link.finding.source.summaries
    return links


def _build_finding_entry(link: FindingResearchArea) -> ResearchAreaFindingEntry:
    f = link.finding
    src = f.source
    tags = [st.tag.name for st in src.source_tags]
    latest_summary = (
        sorted(src.summaries, key=lambda s: s.created_at, reverse=True)[0]
        if src.summaries else None
    )
    summary_short = latest_summary.research_question[:200] if latest_summary else None
    return ResearchAreaFindingEntry(
        link_id=link.id,
        finding_id=f.id,
        relevance=link.relevance,
        relation_type=link.relation_type,
        user_comment=link.user_comment or "",
        claim=f.claim,
        evidence_quote=f.evidence_quote or "",
        evidence_text=f.evidence_text or "",
        page_start=f.page_start,
        page_end=f.page_end,
        confidence=f.confidence,
        validation_status=f.validation_status or "no_evidence",
        validation_method=getattr(f, "validation_method", None) or "none",
        finding_review_status=f.review_status or "unreviewed",
        finding_review_comment=getattr(f, "review_comment", None) or "",
        source_id=src.id,
        source_title=src.title,
        authors=src.authors or "",
        year=src.year,
        doi=src.doi or "",
        tags=tags,
        summary_short=summary_short,
        created_at=f.created_at,
        updated_at=getattr(f, "reviewed_at", None),
    )


@router.get("", response_model=list[ResearchAreaRead])
def list_areas(db: Session = Depends(get_db)):
    return (
        db.query(ResearchArea)
        .order_by(ResearchArea.sort_order, ResearchArea.title)
        .all()
    )


@router.post("", response_model=ResearchAreaRead, status_code=201)
def create_area(body: ResearchAreaCreate, db: Session = Depends(get_db)):
    area = ResearchArea(**body.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.get("/{area_id}", response_model=ResearchAreaRead)
def get_area(area_id: int, db: Session = Depends(get_db)):
    return _get_area_or_404(area_id, db)


@router.patch("/{area_id}", response_model=ResearchAreaRead)
def update_area(area_id: int, body: ResearchAreaUpdate, db: Session = Depends(get_db)):
    area = _get_area_or_404(area_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(area, field, value)
    db.commit()
    db.refresh(area)
    return area


@router.delete("/{area_id}")
def delete_area(area_id: int, db: Session = Depends(get_db)):
    area = _get_area_or_404(area_id, db)
    db.delete(area)  # cascade deletes FindingResearchArea + SourceResearchArea
    db.commit()
    return {"ok": True}


@router.post("/{area_id}/findings", response_model=ResearchAreaFindingEntry, status_code=201)
def assign_finding(area_id: int, body: FindingAssignCreate, db: Session = Depends(get_db)):
    _get_area_or_404(area_id, db)
    finding = db.get(Finding, body.finding_id)
    if not finding:
        raise HTTPException(404, "Finding nicht gefunden")
    link = FindingResearchArea(
        finding_id=body.finding_id,
        research_area_id=area_id,
        relevance=body.relevance,
        relation_type=body.relation_type,
        user_comment=body.user_comment,
    )
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Finding ist dieser Area bereits zugeordnet")
    db.refresh(link)
    links = _load_links(area_id, db, {"include_unreviewed": True})
    link = next(lk for lk in links if lk.id == link.id)
    return _build_finding_entry(link)


@router.patch("/{area_id}/findings/{finding_id}", response_model=ResearchAreaFindingEntry)
def update_finding_assignment(
    area_id: int, finding_id: int, body: FindingAssignUpdate, db: Session = Depends(get_db)
):
    link = db.query(FindingResearchArea).filter_by(
        research_area_id=area_id, finding_id=finding_id
    ).first()
    if not link:
        raise HTTPException(404, "Zuordnung nicht gefunden")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(link, field, value)
    db.commit()
    links = _load_links(area_id, db, {"include_unreviewed": True})
    link = next(lk for lk in links if lk.finding_id == finding_id)
    return _build_finding_entry(link)


@router.delete("/{area_id}/findings/{finding_id}")
def remove_finding_assignment(area_id: int, finding_id: int, db: Session = Depends(get_db)):
    link = db.query(FindingResearchArea).filter_by(
        research_area_id=area_id, finding_id=finding_id
    ).first()
    if not link:
        raise HTTPException(404, "Zuordnung nicht gefunden")
    db.delete(link)
    db.commit()
    return {"ok": True}


@router.get("/{area_id}/findings", response_model=list[ResearchAreaFindingEntry])
def list_area_findings(
    area_id: int,
    include_unreviewed: bool = Query(True),
    review_status: Optional[str] = Query(None),
    validation_status: Optional[str] = Query(None),
    relation_type: Optional[str] = Query(None),
    relevance: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _get_area_or_404(area_id, db)
    links = _load_links(area_id, db, {
        "include_unreviewed": include_unreviewed,
        "review_status": review_status,
        "validation_status": validation_status,
        "relation_type": relation_type,
        "relevance": relevance,
    })
    return [_build_finding_entry(link) for link in links]
