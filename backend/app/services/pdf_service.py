import io
import re
from typing import Any
import fitz


def _fix_encoding(s: str) -> str:
    """Repair strings where PDF/XMP UTF-8 bytes were misread as cp1252/Latin-1."""
    import html as _html
    s = _html.unescape(s)  # convert &#x80; etc. left by PyMuPDF XMP parser
    for _ in range(3):
        try:
            fixed = s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                fixed = s.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
        if fixed == s:
            break
        s = fixed
    return s


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
    raw_title = _fix_encoding(meta.get("title", "") or "")
    raw_author = _fix_encoding(meta.get("author", "") or "")
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
