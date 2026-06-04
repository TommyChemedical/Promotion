import io
import re
from typing import Any
import fitz


def extract_text_from_pdf(file_bytes: bytes) -> list[dict[str, Any]]:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        raise ValueError("Ungültiges PDF")

    pages = []
    for page in doc:
        text = page.get_text("text").strip()
        if text:
            pages.append({"page_number": page.number + 1, "text": text})
    return pages


# DOI regex: matches 10.XXXX/... in plain text, after "DOI:", after "doi.org/", etc.
_DOI_PATTERN = re.compile(
    r'(?:doi\.org/|DOI:\s*|doi:\s*)?'
    r'(10\.\d{4,9}/[^\s,;>\])"\']+)',
    re.IGNORECASE,
)


def extract_metadata_from_pdf(file_bytes: bytes) -> dict[str, Any]:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return {"title": "", "authors": "", "year": None, "doi": "", "journal": ""}

    meta = doc.metadata or {}
    raw_title = meta.get("title", "") or ""
    raw_author = meta.get("author", "") or ""
    raw_date = meta.get("creationDate", "") or ""

    year = None
    year_match = re.search(r"\d{4}", raw_date)
    if year_match:
        year = int(year_match.group())

    # Scan first 3 pages for DOI
    doi = ""
    for page in list(doc)[:3]:
        page_text = page.get_text("text")
        m = _DOI_PATTERN.search(page_text)
        if m:
            doi = m.group(1).rstrip(".")  # strip trailing dot artefacts
            break

    return {
        "title": raw_title.strip(),
        "authors": raw_author.strip(),
        "year": year,
        "doi": doi,
        "journal": "",
    }
