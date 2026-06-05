# LiteraturKI Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix five concrete weaknesses in the MVP: correct model IDs, DOI extraction from text, chunked summarization for long papers, automatic Finding creation from summary key_results, and FTS error logging.

**Architecture:** All changes are isolated to existing backend files. No new endpoints, no schema changes. Each fix is self-contained and independently testable. The chunking approach splits document pages into groups of ≤8,000 chars, runs the LLM once per chunk, then merges key_results arrays while using the first chunk's metadata fields.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, PyMuPDF, anthropic SDK 0.54, pytest

---

## Task 1: Fix Model IDs in .env.example and .env

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/.env`

**Context:** The correct Anthropic model ID for Haiku 4.5 is `claude-haiku-4-5-20251001` (requires the date suffix). Sonnet 4.6 (`claude-sonnet-4-6`) is correct as-is.

**Step 1: Update .env.example**

In `backend/.env.example`, change line 2:
```
# Before:
ANTHROPIC_MODEL_FAST=claude-haiku-4-5

# After:
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
```

**Step 2: Update .env**

Same change in `backend/.env`:
```
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
```

**Step 3: Run tests to confirm nothing broke**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: 41 passed

**Step 4: Commit**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/.env.example
git commit -m "fix: correct Haiku model ID to claude-haiku-4-5-20251001"
```

Note: `.env` is gitignored — do NOT commit it.

---

## Task 2: DOI Extraction from PDF Full Text

**Files:**
- Modify: `backend/app/services/pdf_service.py`
- Modify: `backend/tests/test_pdf_service.py`

**Context:** DOIs follow the pattern `10.XXXX/...`. They appear in PDF text as "DOI: 10.1234/abc", "doi.org/10.1234/abc", or bare "10.1234/abc". PDF metadata rarely contains them; the first two pages of text are the reliable source.

**Step 1: Write the failing test**

Add to `backend/tests/test_pdf_service.py`:

```python
def test_extract_doi_from_text():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Title: Test Paper\nDOI: 10.1038/nature12345\nAbstract: ...")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    meta = extract_metadata_from_pdf(buf.read())
    assert meta["doi"] == "10.1038/nature12345"


def test_extract_doi_from_url_form():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Available at https://doi.org/10.1016/j.cell.2023.01.001")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    meta = extract_metadata_from_pdf(buf.read())
    assert meta["doi"] == "10.1016/j.cell.2023.01.001"


def test_no_doi_returns_empty_string(sample_pdf_bytes):
    meta = extract_metadata_from_pdf(sample_pdf_bytes)
    assert meta["doi"] == ""
```

**Step 2: Run to verify failure**

```bash
PYTHONPATH=. pytest tests/test_pdf_service.py::test_extract_doi_from_text -v 2>&1 | tail -5
```

Expected: FAILED (doi returns "")

**Step 3: Update `extract_metadata_from_pdf` in `backend/app/services/pdf_service.py`**

Replace the entire `extract_metadata_from_pdf` function:

```python
# DOI regex: matches 10.XXXX/... in plain text, after "DOI:", or after "doi.org/"
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

    # Scan first 3 pages for DOI (most papers put it on page 1 or 2)
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
```

**Step 4: Run tests**

```bash
PYTHONPATH=. pytest tests/test_pdf_service.py -v
```

Expected: All 7 tests PASSED

**Step 5: Commit**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/services/pdf_service.py backend/tests/test_pdf_service.py
git commit -m "feat: extract DOI from PDF full text via regex"
```

---

## Task 3: Chunked Summarization for Long Papers

**Files:**
- Modify: `backend/app/api/summarize.py`
- Modify: `backend/tests/test_summarize_api.py`

**Context:** Currently the endpoint truncates at 12,000 chars. Instead: split pages into chunks of ≤8,000 chars each, run the LLM once per chunk, then merge — combining all `key_results` arrays while using the first chunk's metadata fields (research_question, methods, etc.). For short papers (≤8,000 chars total) behavior is identical to before.

**Step 1: Write the failing test**

Add to `backend/tests/test_summarize_api.py`:

```python
def test_summarize_uses_all_chunks_for_long_paper(client_with_source):
    """LLM should be called once per chunk when text exceeds CHUNK_SIZE."""
    client, source_id = client_with_source
    call_count = 0

    def multi_call_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=json.dumps({
            "research_question": f"Question from chunk {call_count}",
            "methods": "RCT",
            "data_basis": "Data",
            "key_results": [{"claim": f"Result {call_count}", "evidence_text": "evidence", "page_number": 1, "confidence": "high"}],
            "limitations": "None",
            "relevance": "High",
            "uncertainty_notes": "",
        }))]
        return mock_msg

    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.side_effect = multi_call_side_effect
        # Patch CHUNK_SIZE to force chunking even on the small test PDF
        import app.api.summarize as summarize_mod
        original = summarize_mod.CHUNK_SIZE
        summarize_mod.CHUNK_SIZE = 5  # force every page to be its own chunk
        try:
            r = client.post(f"/api/sources/{source_id}/summarize")
        finally:
            summarize_mod.CHUNK_SIZE = original

    assert r.status_code == 200
    data = r.json()
    # key_results should be merged from all chunks
    results = json.loads(data["key_results"])
    assert len(results) >= 1
    # research_question comes from first chunk
    assert "chunk 1" in data["research_question"] or data["research_question"] != ""
```

**Step 2: Run to verify failure**

```bash
PYTHONPATH=. pytest tests/test_summarize_api.py::test_summarize_uses_all_chunks_for_long_paper -v 2>&1 | tail -10
```

**Step 3: Rewrite `backend/app/api/summarize.py`**

Replace the full file content:

```python
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


def _build_chunks(texts: list[DocumentText], max_chars: int) -> list[str]:
    """Group pages into text chunks, each at most max_chars characters."""
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
    return chunks[:MAX_CHUNKS]


def _merge_summaries(results: list[dict]) -> dict:
    """Merge LLM outputs from multiple chunks into one summary dict."""
    if not results:
        return {}
    merged = {
        "research_question": next((r["research_question"] for r in results if r.get("research_question")), ""),
        "methods": next((r["methods"] for r in results if r.get("methods")), ""),
        "data_basis": next((r["data_basis"] for r in results if r.get("data_basis")), ""),
        "limitations": next((r["limitations"] for r in results if r.get("limitations")), ""),
        "relevance": next((r["relevance"] for r in results if r.get("relevance")), ""),
        "uncertainty_notes": " | ".join(r["uncertainty_notes"] for r in results if r.get("uncertainty_notes")),
        "key_results": [kr for r in results for kr in r.get("key_results", [])],
    }
    return merged


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

    # Auto-create Finding records from key_results (Task 4 behaviour)
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
```

Note: This single rewrite covers **both Task 3 (chunking) and Task 4 (auto-Finding creation)** since they live in the same function. Task 4 is implemented in the last loop before `db.commit()`.

**Step 4: Run all tests**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: All 42+ tests pass

**Step 5: Commit**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/api/summarize.py backend/tests/test_summarize_api.py
git commit -m "feat: chunked summarization for long papers, auto-create Finding from key_results"
```

---

## Task 4: FTS Error Logging

**Files:**
- Modify: `backend/app/services/search_service.py`
- Modify: `backend/tests/test_search.py`

**Context:** Currently `except Exception: return []` swallows all errors silently. Add logging so the cause is visible in server logs, while still returning `[]` for graceful degradation.

**Step 1: Write the failing test**

Add to `backend/tests/test_search.py`:

```python
def test_search_logs_error_on_bad_query(db_with_indexed_source, caplog):
    """Malformed FTS query should log a warning and return []."""
    import logging
    engine, _ = db_with_indexed_source
    with caplog.at_level(logging.WARNING, logger="app.services.search_service"):
        results = search_fulltext(engine, '"unclosed_quote')
    assert results == []
    assert len(caplog.records) >= 1
```

**Step 2: Run to verify failure**

```bash
PYTHONPATH=. pytest tests/test_search.py::test_search_logs_error_on_bad_query -v 2>&1 | tail -10
```

Expected: FAILED (no log record captured)

**Step 3: Update `backend/app/services/search_service.py`**

Replace the full file:

```python
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def index_document_text(engine: Engine, rowid: int, content: str, source_id: int, page_number: int) -> None:
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO document_text_fts(rowid, text, source_id, page_number) VALUES (:r, :t, :s, :p)"),
            {"r": rowid, "t": content, "s": source_id, "p": page_number},
        )
        conn.commit()


def search_fulltext(engine: Engine, query: str, limit: int = 50) -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT source_id, page_number,
                           snippet(document_text_fts, 0, '[[', ']]', '...', 20) AS snippet
                    FROM document_text_fts
                    WHERE text MATCH :q
                    LIMIT :limit
                """),
                {"q": query, "limit": limit},
            ).fetchall()
        return [{"source_id": r.source_id, "page_number": r.page_number, "snippet": r.snippet} for r in rows]
    except Exception as e:
        logger.warning("FTS search failed for query %r: %s", query, e)
        return []
```

**Step 4: Run all tests**

```bash
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: All tests pass

**Step 5: Commit + push**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/services/search_service.py backend/tests/test_search.py
git commit -m "fix: log FTS search errors instead of silently swallowing them"
git push
```

---

## Execution Checklist

- [ ] Task 1: Fix model IDs in .env.example
- [ ] Task 2: DOI extraction from PDF text
- [ ] Task 3+4: Chunked summarization + auto-Finding creation (one rewrite)
- [ ] Task 5: FTS error logging
