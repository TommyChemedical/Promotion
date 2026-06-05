import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Finding, DocumentText

_STOPWORDS = frozenset({
    "the", "and", "for", "are", "was", "were", "with", "that", "this",
    "from", "have", "has", "had", "not", "but", "they", "their", "than",
    "its", "also", "been", "more", "one", "all", "can", "when", "into",
    "our", "who", "each", "which", "any", "both", "did", "does",
})


@dataclass
class ValidationResult:
    status: str   # "no_evidence" | "invalid_page" | "evidence_found" | "evidence_not_found"
    method: str   # "none" | "exact" | "fragment" | "fuzzy"
    score: float  # 0.0-1.0


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[‐‐-―−]", "-", text)
    text = re.sub(r"[‘’‚‛]", "'", text)
    text = re.sub(r'[“”„‟«»]', '"', text)
    return " ".join(text.split())


def _split_clauses(text: str) -> list:
    parts = re.split(r"[,;]", text)
    return [p.strip() for p in parts if len(p.strip()) >= 15]


def _sliding_fuzzy(quote: str, text: str) -> float:
    window = len(quote) + max(5, len(quote) // 10)
    if len(text) <= window:
        return SequenceMatcher(None, quote, text).ratio()
    step = max(1, len(quote) // 4)
    best = 0.0
    for i in range(0, len(text) - window + 1, step):
        r = SequenceMatcher(None, quote, text[i : i + window]).ratio()
        if r > best:
            best = r
    return best


def _central_token_guard(quote: str, text: str, threshold: float = 0.60) -> bool:
    content = [w for w in quote.split() if len(w) >= 4 and w not in _STOPWORDS]
    if not content:
        return True
    text_words = set(text.split())
    matched = sum(1 for w in content if w in text_words)
    return matched / len(content) >= threshold


def validate_finding_evidence(finding: Finding, db: Session) -> ValidationResult:
    if not finding.evidence_quote or not finding.evidence_quote.strip():
        return ValidationResult(status="no_evidence", method="none", score=0.0)

    page_start = finding.page_start
    if page_start is None or page_start < 1:
        return ValidationResult(status="invalid_page", method="none", score=0.0)

    doc_text = (
        db.query(DocumentText)
        .filter_by(source_id=finding.source_id, page_number=page_start)
        .first()
    )
    if doc_text is None:
        return ValidationResult(status="invalid_page", method="none", score=0.0)

    page_text = doc_text.text
    if finding.page_end is not None and finding.page_end > page_start:
        next_doc = (
            db.query(DocumentText)
            .filter_by(source_id=finding.source_id, page_number=finding.page_end)
            .first()
        )
        if next_doc is not None:
            page_text = page_text + " " + next_doc.text

    norm_quote = _normalize(finding.evidence_quote)
    norm_text = _normalize(page_text)

    if norm_quote in norm_text:
        return ValidationResult(status="evidence_found", method="exact", score=1.0)

    clauses = _split_clauses(norm_quote)
    if clauses:
        found = sum(1 for c in clauses if c in norm_text)
        score = found / len(clauses)
        if score >= 0.60:
            return ValidationResult(status="evidence_found", method="fragment", score=score)

    fuzzy_score = _sliding_fuzzy(norm_quote, norm_text)
    if fuzzy_score >= 0.88 and _central_token_guard(norm_quote, norm_text):
        return ValidationResult(status="evidence_found", method="fuzzy", score=fuzzy_score)

    return ValidationResult(status="evidence_not_found", method="none", score=0.0)


def get_page_preview(
    source_id: int,
    page_number: Optional[int],
    db: Session,
    evidence_quote: str = "",
    max_len: int = 300,
) -> str:
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
    if evidence_quote and evidence_quote.strip():
        anchor = " ".join(_normalize(evidence_quote).split()[:5])
        if anchor:
            idx = text.lower().find(anchor)
            if idx >= 0:
                start = max(0, idx - 50)
                return text[start : start + max_len]
    return text[:max_len]
