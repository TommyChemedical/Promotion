import csv
import io
import json
from sqlalchemy.orm import Session
from app.models import Source

_FORMULA_TRIGGERS = frozenset("=+-@\t\r")


def _sanitize_csv(value: object) -> str:
    s = str(value) if value is not None else ""
    if s and s[0] in _FORMULA_TRIGGERS:
        return "'" + s
    return s


def export_to_csv(db: Session) -> str:
    sources = db.query(Source).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "authors", "year", "doi", "journal", "tags", "filename"])
    for src in sources:
        tags = ",".join(st.tag.name for st in src.source_tags)
        writer.writerow([
            src.id,                        # integer, no sanitization needed
            _sanitize_csv(src.title),
            _sanitize_csv(src.authors or ""),
            src.year or "",                # integer, no sanitization needed
            _sanitize_csv(src.doi or ""),
            _sanitize_csv(src.journal or ""),
            _sanitize_csv(tags),
            _sanitize_csv(src.filename),
        ])
    return buf.getvalue()


def export_to_markdown(db: Session) -> str:
    sources = db.query(Source).all()
    lines: list = ["# LiteraturKI Export\n"]

    for src in sources:
        tags = ", ".join(st.tag.name for st in src.source_tags)
        lines.append(f"# {src.title}")
        lines.append(f"**Autoren:** {src.authors or '—'}  ")
        lines.append(f"**Jahr:** {src.year or '—'}  ")
        lines.append(f"**Journal:** {src.journal or '—'}  ")
        lines.append(f"**Tags:** {tags or '—'}\n")

        if src.summaries:
            s = src.summaries[-1]
            lines.append("## Zusammenfassung")
            lines.append(f"**Forschungsfrage:** {s.research_question}")
            lines.append(f"**Methoden:** {s.methods}")
            lines.append(f"**Datenbasis:** {s.data_basis}")
            lines.append(f"**Limitationen:** {s.limitations}")
            lines.append(f"**Relevanz:** {s.relevance}\n")

            try:
                results = json.loads(s.key_results)
                if results:
                    lines.append("### Kernergebnisse")
                    for r in results:
                        conf = r.get("confidence", "low").upper()
                        lines.append(f"- [{conf}] {r.get('claim', '')}")
                        if r.get("evidence_text"):
                            lines.append(f"  > {r['evidence_text']}")
                        if r.get("page_number"):
                            lines[-1] += f" (S. {r['page_number']})"
                    lines.append("")
            except (json.JSONDecodeError, TypeError):
                pass

        if src.findings:
            lines.append("## Findings")
            for f in src.findings:
                conf = f.confidence.upper()
                lines.append(f"- [{conf}] {f.claim}")
                if f.evidence_text:
                    page_ref = f" (S. {f.page_number})" if f.page_number else ""
                    lines.append(f"  > {f.evidence_text}{page_ref}")
            lines.append("")

        if src.notes:
            lines.append("## Notizen")
            for n in src.notes:
                lines.append(f"- {n.text}")
            lines.append("")

        lines.append("---\n")

    return "\n".join(lines)
