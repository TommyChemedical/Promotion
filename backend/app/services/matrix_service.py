from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from app.models import Source, SourceTag
from app.schemas import MatrixRow, MatrixFilters, MatrixResponse


def build_matrix_rows(db: Session) -> list[MatrixRow]:
    sources = (
        db.query(Source)
        .options(
            selectinload(Source.summaries),
            selectinload(Source.findings),
            selectinload(Source.notes),
            selectinload(Source.source_tags).selectinload(SourceTag.tag),
        )
        .all()
    )
    rows: list[MatrixRow] = []
    for src in sources:
        tags = [st.tag.name for st in src.source_tags]
        notes_count = len(src.notes)
        latest_summary = (
            sorted(src.summaries, key=lambda s: s.created_at or datetime.min, reverse=True)[0]
            if src.summaries else None
        )
        source_review_status = latest_summary.review_status if latest_summary else "unreviewed"
        summary_short = (
            latest_summary.research_question[:200]
            if latest_summary and latest_summary.research_question
            else None
        )
        summary_review_status = latest_summary.review_status if latest_summary else None

        if src.findings:
            for f in src.findings:
                updated_at = f.reviewed_at if f.reviewed_at else src.updated_at
                rows.append(MatrixRow(
                    source_id=src.id,
                    source_title=src.title,
                    authors=src.authors or "",
                    year=src.year,
                    doi=src.doi or "",
                    journal=src.journal or "",
                    source_review_status=source_review_status,
                    finding_id=f.id,
                    finding_statement=f.claim,
                    finding_page_start=f.page_start,
                    finding_page_end=f.page_end,
                    evidence_quote=f.evidence_quote or None,
                    validation_status=f.validation_status,
                    validation_method=f.validation_method,
                    validation_score=f.validation_score,
                    finding_review_status=f.review_status,
                    finding_review_comment=f.review_comment or None,
                    confidence_user=f.confidence_user,
                    summary_short=summary_short,
                    summary_review_status=summary_review_status,
                    tags=tags,
                    notes_count=notes_count,
                    created_at=src.created_at,
                    updated_at=updated_at,
                ))
        else:
            rows.append(MatrixRow(
                source_id=src.id,
                source_title=src.title,
                authors=src.authors or "",
                year=src.year,
                doi=src.doi or "",
                journal=src.journal or "",
                source_review_status=source_review_status,
                finding_id=None,
                finding_statement=None,
                finding_page_start=None,
                finding_page_end=None,
                evidence_quote=None,
                validation_status=None,
                validation_method=None,
                validation_score=None,
                finding_review_status=None,
                finding_review_comment=None,
                confidence_user=None,
                summary_short=summary_short,
                summary_review_status=summary_review_status,
                tags=tags,
                notes_count=notes_count,
                created_at=src.created_at,
                updated_at=src.updated_at,
            ))
    return rows


def apply_filters(rows: list[MatrixRow], filters: MatrixFilters) -> list[MatrixRow]:
    result = rows

    if filters.q:
        q = filters.q.lower()
        result = [
            r for r in result
            if q in (r.source_title or "").lower()
            or q in (r.authors or "").lower()
            or q in (r.finding_statement or "").lower()
            or q in (r.summary_short or "").lower()
        ]

    if filters.tag:
        result = [r for r in result if all(t in r.tags for t in filters.tag)]

    if filters.year_from is not None:
        result = [r for r in result if r.year is not None and r.year >= filters.year_from]

    if filters.year_to is not None:
        result = [r for r in result if r.year is not None and r.year <= filters.year_to]

    if filters.review_status:
        result = [
            r for r in result
            if r.finding_review_status == filters.review_status
            or r.source_review_status == filters.review_status
        ]

    if filters.validation_status:
        result = [r for r in result if r.validation_status == filters.validation_status]

    if filters.has_evidence is True:
        result = [r for r in result if r.validation_status == "evidence_found"]

    if filters.has_evidence is False:
        result = [r for r in result if r.validation_status != "evidence_found"]

    if filters.only_reviewed:
        result = [
            r for r in result
            if r.finding_review_status not in (None, "unreviewed")
            or r.source_review_status != "unreviewed"
        ]

    if filters.only_unreviewed:
        result = [
            r for r in result
            if r.finding_review_status in (None, "unreviewed")
            and r.source_review_status == "unreviewed"
        ]

    if filters.source_id is not None:
        result = [r for r in result if r.source_id == filters.source_id]

    _SORT_KEYS = {
        "year": lambda r: (r.year is None, r.year or 0),
        "title": lambda r: (r.source_title or "").lower(),
        "created_at": lambda r: r.created_at or datetime.min,
        "updated_at": lambda r: r.updated_at or datetime.min,
        "review_status": lambda r: r.finding_review_status or r.source_review_status or "",
        "validation_status": lambda r: r.validation_status or "",
    }
    key_fn = _SORT_KEYS.get(filters.sort_by, _SORT_KEYS["created_at"])
    result = sorted(result, key=key_fn, reverse=(filters.sort_order == "desc"))

    return result


def build_response(
    filtered: list[MatrixRow],
    filters: MatrixFilters,
    all_rows: list[MatrixRow],
) -> MatrixResponse:
    total = len(filtered)
    page = filtered[filters.offset : filters.offset + filters.limit]

    filters_applied: dict = {}
    if filters.q:
        filters_applied["q"] = filters.q
    if filters.tag:
        filters_applied["tag"] = filters.tag
    if filters.year_from is not None:
        filters_applied["year_from"] = filters.year_from
    if filters.year_to is not None:
        filters_applied["year_to"] = filters.year_to
    if filters.review_status:
        filters_applied["review_status"] = filters.review_status
    if filters.validation_status:
        filters_applied["validation_status"] = filters.validation_status
    if filters.has_evidence is not None:
        filters_applied["has_evidence"] = filters.has_evidence
    if filters.only_reviewed:
        filters_applied["only_reviewed"] = True
    if filters.only_unreviewed:
        filters_applied["only_unreviewed"] = True
    if filters.source_id is not None:
        filters_applied["source_id"] = filters.source_id

    return MatrixResponse(
        items=page,
        total=total,
        limit=filters.limit,
        offset=filters.offset,
        filters_applied=filters_applied,
    )


def export_matrix_csv(rows: list[MatrixRow]) -> str:
    import csv
    import io
    _FORMULA_TRIGGERS = frozenset("=+-@\t\r")

    def _san(v: object) -> str:
        s = str(v) if v is not None else ""
        return ("'" + s) if s and s[0] in _FORMULA_TRIGGERS else s

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "source_id", "source_title", "authors", "year", "doi", "journal",
        "tags", "notes_count", "source_review_status", "summary_short",
        "summary_review_status", "finding_id", "finding_statement",
        "finding_page_start", "finding_page_end", "evidence_quote",
        "validation_status", "validation_method", "validation_score",
        "finding_review_status", "finding_review_comment", "confidence_user",
        "created_at", "updated_at",
    ])
    for r in rows:
        writer.writerow([
            r.source_id, _san(r.source_title), _san(r.authors), r.year or "",
            _san(r.doi), _san(r.journal), _san(";".join(r.tags)), r.notes_count,
            r.source_review_status, _san(r.summary_short),
            r.summary_review_status or "", r.finding_id or "",
            _san(r.finding_statement), r.finding_page_start or "",
            r.finding_page_end or "", _san(r.evidence_quote),
            r.validation_status or "", r.validation_method or "",
            r.validation_score if r.validation_score is not None else "",
            r.finding_review_status or "", _san(r.finding_review_comment),
            r.confidence_user or "", r.created_at or "", r.updated_at or "",
        ])
    return buf.getvalue()


def export_matrix_markdown(rows: list[MatrixRow]) -> str:
    lines = ["# Literatur-Matrix Export\n"]
    by_source: dict[int, list[MatrixRow]] = {}
    for r in rows:
        by_source.setdefault(r.source_id, []).append(r)

    for source_rows in by_source.values():
        first = source_rows[0]
        lines.append(f"## {first.source_title}")
        meta = []
        if first.authors:
            meta.append(f"Autor: {first.authors}")
        if first.year:
            meta.append(f"Jahr: {first.year}")
        if first.tags:
            meta.append(f"Tags: {', '.join(first.tags)}")
        if meta:
            lines.append(f"*{' | '.join(meta)}*")
        if first.summary_short:
            lines.append(f"\n**Zusammenfassung:** {first.summary_short}")
        lines.append(f"**Review-Status (Quelle):** {first.source_review_status}")

        for r in source_rows:
            if r.finding_id is None:
                continue
            lines.append(f"\n### Finding #{r.finding_id}")
            lines.append(f"- **Aussage:** {r.finding_statement}")
            lines.append(f"- **Evidenz-Status:** {r.validation_status or '—'} ({r.validation_method or 'none'})")
            lines.append(f"- **Review-Status:** {r.finding_review_status or 'unreviewed'}")
            if r.finding_review_comment:
                lines.append(f"- **Kommentar:** {r.finding_review_comment}")
            if r.evidence_quote:
                lines.append(f"- **Zitat:** *{r.evidence_quote}*")
        lines.append("")

    return "\n".join(lines)
