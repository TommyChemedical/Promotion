import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Source, Summary, LLMRun, DocumentText, Finding
from app.schemas import SummaryRead
from app.services.llm_service import llm_service, ModelTier

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8_000   # max chars per LLM chunk
MAX_CHUNKS = 10      # safety cap to avoid runaway API costs

router = APIRouter(prefix="/api/sources", tags=["summarize"])

PROMPT_DIR = Path(__file__).parent.parent / "prompts"
SUMMARY_VERSION = "summary_v1"


def _load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def _parse_llm_json(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        inner = [l for l in lines[1:] if l.strip() != "```"]
        clean = "\n".join(inner)
    return json.loads(clean)


def _build_chunks(texts: list, max_chars: int) -> list[str]:
    """Group DocumentText pages into text chunks, each at most max_chars characters."""
    chunks: list[str] = []
    current_parts: list[str] = []
    current_size = 0
    for t in texts:
        part = f"[Seite {t.page_number}]\n{t.text}"
        if current_parts and current_size + len(part) > max_chars:
            chunks.append("\n\n".join(current_parts))
            current_parts = [part]
            current_size = len(part)
        else:
            current_parts.append(part)
            current_size += len(part)
    if current_parts:
        chunks.append("\n\n".join(current_parts))
    if len(chunks) > MAX_CHUNKS:
        logger.warning("Source text exceeded MAX_CHUNKS=%d; %d chunk(s) dropped", MAX_CHUNKS, len(chunks) - MAX_CHUNKS)
    return chunks[:MAX_CHUNKS]


def _merge_summaries(results: list[dict]) -> dict:
    """Merge LLM outputs from multiple chunks into one summary dict."""
    if not results:
        return {}
    return {
        "research_question": next((r["research_question"] for r in results if r.get("research_question")), ""),
        "methods":           next((r["methods"]           for r in results if r.get("methods")), ""),
        "data_basis":        next((r["data_basis"]        for r in results if r.get("data_basis")), ""),
        "limitations":       next((r["limitations"]       for r in results if r.get("limitations")), ""),
        "relevance":         next((r["relevance"]         for r in results if r.get("relevance")), ""),
        "uncertainty_notes": " | ".join(r["uncertainty_notes"] for r in results if r.get("uncertainty_notes")),
        "key_results":       [kr for r in results for kr in r.get("key_results", [])],
    }


@router.post("/{source_id}/summarize", response_model=SummaryRead)
def summarize_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")

    texts = (
        db.query(DocumentText)
        .filter_by(source_id=source_id)
        .order_by(DocumentText.page_number)
        .all()
    )
    if not texts:
        raise HTTPException(400, "Kein extrahierter Text vorhanden")

    # Delete existing summary and findings before re-summarizing
    db.query(Summary).filter_by(source_id=source_id).delete()
    db.query(Finding).filter_by(source_id=source_id).delete()

    chunks = _build_chunks(texts, CHUNK_SIZE)
    template = _load_prompt(SUMMARY_VERSION)
    chunk_results: list[dict] = []

    logger.info("Source %d: summarizing %d chunk(s) from %d pages", source_id, len(chunks), len(texts))

    for i, chunk_text in enumerate(chunks):
        prompt = template.replace("{text}", chunk_text)
        try:
            raw = llm_service.run(prompt, ModelTier.DEEP, task_type="summarize", prompt_version=SUMMARY_VERSION)
        except RuntimeError as e:
            raise HTTPException(502, str(e))
        try:
            data = _parse_llm_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(500, f"LLM hat kein valides JSON zurückgegeben (Chunk {i + 1}): {e}")
        chunk_results.append(data)
        db.add(LLMRun(
            source_id=source_id,
            task_type="summarize",
            model_name=llm_service.model_name_for_tier(ModelTier.DEEP),
            prompt_version=SUMMARY_VERSION,
            prompt=prompt[:5000],
            output_json=raw[:10000],
        ))

    merged = _merge_summaries(chunk_results)

    summary = Summary(
        source_id=source_id,
        model_name=llm_service.model_name_for_tier(ModelTier.DEEP),
        prompt_version=SUMMARY_VERSION,
        research_question=merged.get("research_question", ""),
        methods=merged.get("methods", ""),
        data_basis=merged.get("data_basis", ""),
        key_results=json.dumps(merged.get("key_results", []), ensure_ascii=False),
        limitations=merged.get("limitations", ""),
        relevance=merged.get("relevance", ""),
        uncertainty_notes=merged.get("uncertainty_notes", ""),
    )
    db.add(summary)

    # Auto-create Finding records from key_results
    for kr in merged.get("key_results", []):
        db.add(Finding(
            source_id=source_id,
            claim=kr.get("claim", ""),
            evidence_text=kr.get("evidence_text", ""),
            page_number=kr.get("page_number"),
            confidence=kr.get("confidence", "low"),
        ))

    db.commit()
    db.refresh(summary)
    return summary
