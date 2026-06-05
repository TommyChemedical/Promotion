from typing import Optional
from sqlalchemy.orm import Session
from app.models import Finding, DocumentText


def _normalize(text: str) -> str:
    """Lowercase and collapse all whitespace to single spaces."""
    return " ".join(text.lower().split())


def _word_overlap(quote_norm: str, text_norm: str) -> float:
    """Fraction of quote words that appear in text words."""
    q_words = set(quote_norm.split())
    if not q_words:
        return 0.0
    t_words = set(text_norm.split())
    return len(q_words & t_words) / len(q_words)


def validate_finding_evidence(finding: Finding, db: Session) -> str:
    """
    Check whether finding.evidence_quote appears in the extracted page text.

    Returns:
        "no_evidence"         – evidence_quote is empty
        "evidence_found"      – exact or fuzzy match (>=75% word overlap)
        "evidence_not_found"  – page exists but quote not found; or page missing
    """
    if not finding.evidence_quote or not finding.evidence_quote.strip():
        return "no_evidence"

    if finding.page_number is None:
        return "evidence_not_found"

    doc_text = (
        db.query(DocumentText)
        .filter_by(source_id=finding.source_id, page_number=finding.page_number)
        .first()
    )
    if doc_text is None:
        return "evidence_not_found"

    norm_quote = _normalize(finding.evidence_quote)
    norm_text = _normalize(doc_text.text)

    if norm_quote in norm_text:
        return "evidence_found"

    if _word_overlap(norm_quote, norm_text) >= 0.75:
        return "evidence_found"

    return "evidence_not_found"


def get_page_preview(source_id: int, page_number: Optional[int], db: Session,
                     evidence_quote: str = "", max_len: int = 300) -> str:
    """Return a short excerpt of the page text, centred near the evidence quote if possible."""
    if page_number is None:
        return ""
    doc_text = (
        db.query(DocumentText)
        .filter_by(source_id=source_id, page_number=page_number)
        .first()
    )
    if doc_text is None:
        return ""
    text = doc_text.text
    if evidence_quote:
        first_word = evidence_quote.lower().split()[0] if evidence_quote.split() else ""
        idx = text.lower().find(first_word) if first_word else -1
        if idx >= 0:
            start = max(0, idx - 50)
            return text[start: start + max_len]
    return text[:max_len]
