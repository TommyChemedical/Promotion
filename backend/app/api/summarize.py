import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Source, Summary, LLMRun, DocumentText
from app.schemas import SummaryRead
from app.services.llm_service import llm_service, ModelTier

logger = logging.getLogger(__name__)
MAX_PROMPT_CHARS = 12_000

router = APIRouter(prefix="/api/sources", tags=["summarize"])

PROMPT_DIR = Path(__file__).parent.parent / "prompts"
SUMMARY_VERSION = "summary_v1"


def _load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def _parse_llm_json(raw: str) -> dict:
    clean = raw.strip()
    # Strip markdown code fences if present
    if clean.startswith("```"):
        lines = clean.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner = [l for l in lines[1:] if l.strip() != "```"]
        clean = "\n".join(inner)
    return json.loads(clean)


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
    full_text = "\n\n".join(f"[Seite {t.page_number}]\n{t.text}" for t in texts)

    if not full_text.strip():
        raise HTTPException(400, "Kein extrahierter Text vorhanden")

    template = _load_prompt(SUMMARY_VERSION)
    truncated = full_text[:MAX_PROMPT_CHARS]
    if len(full_text) > MAX_PROMPT_CHARS:
        logger.warning(
            "Source %d: text truncated from %d to %d chars for LLM prompt",
            source_id, len(full_text), MAX_PROMPT_CHARS,
        )
    prompt = template.replace("{text}", truncated)

    try:
        raw = llm_service.run(prompt, ModelTier.DEEP, task_type="summarize", prompt_version=SUMMARY_VERSION)
    except RuntimeError as e:
        raise HTTPException(502, str(e))

    try:
        data = _parse_llm_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(500, f"LLM hat kein valides JSON zurückgegeben: {e}")

    summary = Summary(
        source_id=source_id,
        model_name=llm_service.model_name_for_tier(ModelTier.DEEP),
        prompt_version=SUMMARY_VERSION,
        research_question=data.get("research_question", ""),
        methods=data.get("methods", ""),
        data_basis=data.get("data_basis", ""),
        key_results=json.dumps(data.get("key_results", []), ensure_ascii=False),
        limitations=data.get("limitations", ""),
        relevance=data.get("relevance", ""),
        uncertainty_notes=data.get("uncertainty_notes", ""),
    )
    db.add(summary)

    run = LLMRun(
        source_id=source_id,
        task_type="summarize",
        model_name=llm_service.model_name_for_tier(ModelTier.DEEP),
        prompt_version=SUMMARY_VERSION,
        prompt=prompt[:5000],
        output_json=raw[:10000],
    )
    db.add(run)
    db.commit()
    db.refresh(summary)
    return summary
