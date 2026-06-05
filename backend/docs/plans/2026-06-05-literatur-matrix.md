# Literatur-Matrix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a flat "Literatur-Matrix" with backend API (`GET /api/matrix`, CSV/MD export) and a Next.js frontend page (`/matrix`) showing one row per finding (sources without findings get an empty row), with filters, status badges, and export buttons.

**Architecture:** Python service builds flat MatrixRow list from ORM objects in memory (correct for small datasets), applies filters/sort/pagination, and serves via FastAPI. Frontend is a client component with a "Suchen" button that fetches from `/api/matrix` with query params, renders a table with status badges, truncated text, and export buttons that pass current filter state.

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy 2.x, Pydantic v2, Next.js 16.2.7 App Router, React 19, TypeScript, Tailwind CSS v4

---

## Context for all tasks

**Repo layout (backend):**
- `app/models.py` — SQLAlchemy models: Source, Summary, Finding, Note, SourceTag, Tag
- `app/schemas.py` — Pydantic v2 schemas (ReviewStatus, ValidationStatus, ValidationMethod already defined)
- `app/services/` — business logic (evidence_service.py, export_service.py)
- `app/api/` — FastAPI routers (sources, search, summarize, export, review)
- `app/main.py` — registers routers + calls init_db() on startup
- `tests/` — pytest tests using in-memory SQLite fixtures

**Frontend layout:**
- `app/layout.tsx` — nav with: Quellen, Hochladen, Suche, Export
- `lib/api.ts` — typed fetch wrapper, all API calls go here
- `components/review/` — existing review components for reference

**Migration pattern (no Alembic):** No new DB columns needed for matrix — it's a read-only view over existing data.

**Key model fields:**
- `Source`: id, title, authors, year, doi, journal, created_at, updated_at, source_tags→tag.name, notes (count), summaries, findings
- `Summary`: review_status (default "unreviewed"), research_question, reviewed_at
- `Finding`: id, claim, evidence_quote, page_start, page_end, validation_status, validation_method, validation_score, review_status, review_comment, confidence_user, reviewed_at, created_at
- `ReviewStatus` enum values: unreviewed, correct, partially_correct, incorrect, unsupported, missing_important_context
- `ValidationStatus` enum values: no_evidence, evidence_found, evidence_not_found, invalid_page

---

## Task 1: MatrixRow, MatrixFilters, MatrixResponse schemas

**Files:**
- Modify: `app/schemas.py`
- Test: `tests/test_matrix_api.py` (write failing import test first)

**Step 1: Write the failing test**

```python
# tests/test_matrix_api.py
from app.schemas import MatrixRow, MatrixFilters, MatrixResponse

def test_matrix_schemas_importable():
    row = MatrixRow(
        source_id=1, source_title="Test", authors="", year=None, doi="", journal="",
        source_review_status="unreviewed", finding_id=None, finding_statement=None,
        finding_page_start=None, finding_page_end=None, evidence_quote=None,
        validation_status=None, validation_method=None, validation_score=None,
        finding_review_status=None, finding_review_comment=None, confidence_user=None,
        summary_short=None, summary_review_status=None, tags=[], notes_count=0,
        created_at=None, updated_at=None,
    )
    assert row.source_id == 1
    assert row.finding_id is None

def test_matrix_response_structure():
    resp = MatrixResponse(items=[], total=0, limit=100, offset=0, filters_applied={})
    assert resp.total == 0
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
python -m pytest tests/test_matrix_api.py::test_matrix_schemas_importable -v
```
Expected: FAIL with `ImportError: cannot import name 'MatrixRow'`

**Step 3: Add schemas to `app/schemas.py`**

Append to end of `app/schemas.py`:

```python
# --- Matrix types ---

class MatrixRow(BaseModel):
    source_id: int
    source_title: str
    authors: str
    year: Optional[int]
    doi: str
    journal: str
    source_review_status: str
    finding_id: Optional[int]
    finding_statement: Optional[str]
    finding_page_start: Optional[int]
    finding_page_end: Optional[int]
    evidence_quote: Optional[str]
    validation_status: Optional[str]
    validation_method: Optional[str]
    validation_score: Optional[float]
    finding_review_status: Optional[str]
    finding_review_comment: Optional[str]
    confidence_user: Optional[int]
    summary_short: Optional[str]
    summary_review_status: Optional[str]
    tags: list[str]
    notes_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class MatrixFilters(BaseModel):
    q: Optional[str] = None
    tag: list[str] = Field(default_factory=list)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    review_status: Optional[str] = None
    validation_status: Optional[str] = None
    has_evidence: Optional[bool] = None
    only_reviewed: bool = False
    only_unreviewed: bool = False
    source_id: Optional[int] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class MatrixResponse(BaseModel):
    items: list[MatrixRow]
    total: int
    limit: int
    offset: int
    filters_applied: dict
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_matrix_api.py::test_matrix_schemas_importable tests/test_matrix_api.py::test_matrix_response_structure -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/schemas.py tests/test_matrix_api.py
git commit -m "feat: add MatrixRow, MatrixFilters, MatrixResponse schemas"
```

---

## Task 2: matrix_service.py (row building, filtering, sorting, pagination)

**Files:**
- Create: `app/services/matrix_service.py`
- Test: `tests/test_matrix_api.py` (add service-level tests)

**Step 1: Write the failing tests**

Add to `tests/test_matrix_api.py`:

```python
import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, Source, Summary, Finding, Note, SourceTag, Tag
from app.services.matrix_service import build_matrix_rows, apply_filters, build_response
from app.schemas import MatrixFilters


@pytest.fixture
def matrix_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        # Source 1 with summary + finding
        src1 = Source(title="Alpha Study", authors="Smith J", year=2022,
                      doi="10.1/alpha", journal="Nature", filename="a.pdf", file_path="/a.pdf")
        session.add(src1)
        session.flush()

        tag1 = Tag(name="climate")
        session.add(tag1)
        session.flush()
        session.add(SourceTag(source_id=src1.id, tag_id=tag1.id))

        note1 = Note(source_id=src1.id, text="Interesting")
        session.add(note1)

        summary1 = Summary(
            source_id=src1.id, model_name="test", prompt_version="v1",
            research_question="Does X cause Y?", methods="RCT",
            data_basis="100 patients", key_results="[]",
            limitations="", relevance="", uncertainty_notes="",
            review_status="correct",
        )
        session.add(summary1)
        session.flush()

        finding1 = Finding(
            source_id=src1.id,
            claim="X causes Y significantly",
            evidence_quote="significantly reduces Y",
            page_start=3, page_end=3,
            confidence="high",
            validation_status="evidence_found",
            validation_method="exact",
            validation_score=1.0,
            review_status="correct",
            review_comment="Well supported",
            confidence_user=5,
        )
        session.add(finding1)

        # Source 2 without summary or finding
        src2 = Source(title="Beta Paper", authors="Jones A", year=2021,
                      filename="b.pdf", file_path="/b.pdf", doi="", journal="")
        session.add(src2)
        session.commit()

        yield session


def test_build_matrix_rows_with_finding(matrix_db):
    rows = build_matrix_rows(matrix_db)
    # Source 1 has 1 finding → 1 row; Source 2 has no finding → 1 empty row
    assert len(rows) == 2
    row1 = next(r for r in rows if r.source_title == "Alpha Study")
    assert row1.finding_statement == "X causes Y significantly"
    assert row1.validation_status == "evidence_found"
    assert row1.tags == ["climate"]
    assert row1.notes_count == 1
    assert row1.summary_short == "Does X cause Y?"
    assert row1.summary_review_status == "correct"


def test_build_matrix_rows_empty_source(matrix_db):
    rows = build_matrix_rows(matrix_db)
    row2 = next(r for r in rows if r.source_title == "Beta Paper")
    assert row2.finding_id is None
    assert row2.validation_status is None
    assert row2.notes_count == 0


def test_filter_by_q(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filters = MatrixFilters(q="Alpha")
    filtered = apply_filters(rows, filters)
    assert len(filtered) == 1
    assert filtered[0].source_title == "Alpha Study"


def test_filter_by_tag(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filters = MatrixFilters(tag=["climate"])
    filtered = apply_filters(rows, filters)
    assert len(filtered) == 1

    filters_nomatch = MatrixFilters(tag=["medical"])
    assert len(apply_filters(rows, filters_nomatch)) == 0


def test_filter_by_year(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filters = MatrixFilters(year_from=2022, year_to=2023)
    filtered = apply_filters(rows, filters)
    assert all(r.year and r.year >= 2022 for r in filtered)


def test_filter_review_status(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filters = MatrixFilters(review_status="correct")
    filtered = apply_filters(rows, filters)
    assert len(filtered) == 1


def test_filter_validation_status(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filters = MatrixFilters(validation_status="evidence_found")
    filtered = apply_filters(rows, filters)
    assert len(filtered) == 1
    assert filtered[0].validation_status == "evidence_found"


def test_filter_has_evidence_true(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filtered = apply_filters(rows, MatrixFilters(has_evidence=True))
    assert all(r.validation_status == "evidence_found" for r in filtered)


def test_filter_only_unreviewed(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filtered = apply_filters(rows, MatrixFilters(only_unreviewed=True))
    # Source 2 has no summary → source_review_status="unreviewed", finding_review_status=None
    assert all(r.source_review_status == "unreviewed" or r.finding_review_status in (None, "unreviewed") for r in filtered)


def test_filter_by_source_id(matrix_db):
    rows = build_matrix_rows(matrix_db)
    # get source ids from rows
    src1_id = next(r.source_id for r in rows if r.source_title == "Alpha Study")
    filtered = apply_filters(rows, MatrixFilters(source_id=src1_id))
    assert all(r.source_id == src1_id for r in filtered)


def test_sort_by_year_asc(matrix_db):
    rows = build_matrix_rows(matrix_db)
    sorted_rows = apply_filters(rows, MatrixFilters(sort_by="year", sort_order="asc"))
    years = [r.year for r in sorted_rows if r.year is not None]
    assert years == sorted(years)


def test_pagination(matrix_db):
    rows = build_matrix_rows(matrix_db)
    resp = build_response(rows, MatrixFilters(limit=1, offset=0), rows)
    assert resp.total == 2
    assert len(resp.items) == 1
    assert resp.offset == 0


def test_build_response_filters_applied(matrix_db):
    rows = build_matrix_rows(matrix_db)
    filters = MatrixFilters(q="Alpha", limit=100, offset=0)
    filtered = apply_filters(rows, filters)
    resp = build_response(filtered, filters, rows)
    assert resp.filters_applied.get("q") == "Alpha"
```

**Step 2: Run to verify they fail**

```bash
python -m pytest tests/test_matrix_api.py -k "test_build_matrix" -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.matrix_service'`

**Step 3: Create `app/services/matrix_service.py`**

```python
from __future__ import annotations
from sqlalchemy.orm import Session, selectinload
from app.models import Source
from app.schemas import MatrixRow, MatrixFilters, MatrixResponse


def build_matrix_rows(db: Session) -> list[MatrixRow]:
    sources = (
        db.query(Source)
        .options(
            selectinload(Source.summaries),
            selectinload(Source.findings),
            selectinload(Source.notes),
            selectinload(Source.source_tags).selectinload(
                __import__("app.models", fromlist=["SourceTag"]).SourceTag.tag
            ),
        )
        .all()
    )
    rows: list[MatrixRow] = []
    for src in sources:
        tags = [st.tag.name for st in src.source_tags]
        notes_count = len(src.notes)
        latest_summary = sorted(src.summaries, key=lambda s: s.created_at or 0, reverse=True)[0] if src.summaries else None
        source_review_status = latest_summary.review_status if latest_summary else "unreviewed"
        summary_short = (latest_summary.research_question[:200] if latest_summary and latest_summary.research_question else None)
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
        "created_at": lambda r: r.created_at or "",
        "updated_at": lambda r: r.updated_at or "",
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

    for source_id, source_rows in by_source.items():
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
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_matrix_api.py -v
```
Expected: All 16 tests PASS

**Step 5: Commit**

```bash
git add app/schemas.py app/services/matrix_service.py tests/test_matrix_api.py
git commit -m "feat: add matrix_service with row building, filtering, and export"
```

---

## Task 3: matrix.py API router + register in main.py

**Files:**
- Create: `app/api/matrix.py`
- Modify: `app/main.py`
- Test: add HTTP-level tests to `tests/test_matrix_api.py`

**Step 1: Write failing HTTP tests**

Add to `tests/test_matrix_api.py`:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


@pytest.fixture
def matrix_client(matrix_db):
    def override_db():
        yield matrix_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_matrix_200(matrix_client):
    r = matrix_client.get("/api/matrix")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2


def test_get_matrix_filter_q(matrix_client):
    r = matrix_client.get("/api/matrix?q=Alpha")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_get_matrix_export_csv(matrix_client):
    r = matrix_client.get("/api/matrix/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "source_id" in r.text


def test_get_matrix_export_md(matrix_client):
    r = matrix_client.get("/api/matrix/export.md")
    assert r.status_code == 200
    assert "Alpha Study" in r.text


def test_get_matrix_invalid_limit(matrix_client):
    r = matrix_client.get("/api/matrix?limit=0")
    assert r.status_code == 422


def test_get_matrix_pagination(matrix_client):
    r = matrix_client.get("/api/matrix?limit=1&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["total"] == 2
```

**Step 2: Run to verify they fail**

```bash
python -m pytest tests/test_matrix_api.py::test_get_matrix_200 -v
```
Expected: FAIL with `404 Not Found`

**Step 3: Create `app/api/matrix.py`**

```python
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import MatrixFilters, MatrixResponse
from app.services.matrix_service import (
    build_matrix_rows, apply_filters, build_response,
    export_matrix_csv, export_matrix_markdown,
)

router = APIRouter(prefix="/api/matrix", tags=["matrix"])


def _parse_filters(
    q: Optional[str] = Query(None),
    tag: list[str] = Query(default=[]),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None),
    validation_status: Optional[str] = Query(None),
    has_evidence: Optional[bool] = Query(None),
    only_reviewed: bool = Query(False),
    only_unreviewed: bool = Query(False),
    source_id: Optional[int] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> MatrixFilters:
    return MatrixFilters(
        q=q, tag=tag, year_from=year_from, year_to=year_to,
        review_status=review_status, validation_status=validation_status,
        has_evidence=has_evidence, only_reviewed=only_reviewed,
        only_unreviewed=only_unreviewed, source_id=source_id,
        sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset,
    )


@router.get("", response_model=MatrixResponse)
def get_matrix(
    filters: MatrixFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
) -> MatrixResponse:
    all_rows = build_matrix_rows(db)
    filtered = apply_filters(all_rows, filters)
    return build_response(filtered, filters, all_rows)


@router.get("/export.csv")
def export_csv(
    filters: MatrixFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    all_rows = build_matrix_rows(db)
    filtered = apply_filters(all_rows, filters)
    content = export_matrix_csv(filtered)
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=matrix_export.csv"},
    )


@router.get("/export.md")
def export_md(
    filters: MatrixFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    all_rows = build_matrix_rows(db)
    filtered = apply_filters(all_rows, filters)
    content = export_matrix_markdown(filtered)
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=matrix_export.md"},
    )
```

**Step 4: Register router in `app/main.py`**

In `app/main.py`, after the existing router imports and `app.include_router(...)` calls, add:

```python
from app.api.matrix import router as matrix_router
# ...
app.include_router(matrix_router)
```

**Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_matrix_api.py -v
```
Expected: All 22 tests PASS

**Step 6: Commit**

```bash
git add app/api/matrix.py app/main.py tests/test_matrix_api.py
git commit -m "feat: add /api/matrix endpoint with CSV and MD export"
```

---

## Task 4: Frontend API types + getMatrix in lib/api.ts

**Files:**
- Modify: `frontend/lib/api.ts`

**Step 1: Add types and API function**

In `frontend/lib/api.ts`, add after the existing `EvidenceValidationResponse` interface:

```typescript
// --- Matrix types ---

export interface MatrixRow {
  source_id: number;
  source_title: string;
  authors: string;
  year: number | null;
  doi: string;
  journal: string;
  source_review_status: string;
  finding_id: number | null;
  finding_statement: string | null;
  finding_page_start: number | null;
  finding_page_end: number | null;
  evidence_quote: string | null;
  validation_status: string | null;
  validation_method: string | null;
  validation_score: number | null;
  finding_review_status: string | null;
  finding_review_comment: string | null;
  confidence_user: number | null;
  summary_short: string | null;
  summary_review_status: string | null;
  tags: string[];
  notes_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface MatrixResponse {
  items: MatrixRow[];
  total: number;
  limit: number;
  offset: number;
  filters_applied: Record<string, unknown>;
}

export interface MatrixFilters {
  q?: string;
  tag?: string[];
  year_from?: number;
  year_to?: number;
  review_status?: string;
  validation_status?: string;
  has_evidence?: boolean;
  only_reviewed?: boolean;
  only_unreviewed?: boolean;
  source_id?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}
```

Also add to the `api` object at the bottom:

```typescript
  // Matrix
  getMatrix: (filters?: MatrixFilters) => {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.q) params.set("q", filters.q);
      if (filters.tag) filters.tag.forEach((t) => params.append("tag", t));
      if (filters.year_from != null) params.set("year_from", String(filters.year_from));
      if (filters.year_to != null) params.set("year_to", String(filters.year_to));
      if (filters.review_status) params.set("review_status", filters.review_status);
      if (filters.validation_status) params.set("validation_status", filters.validation_status);
      if (filters.has_evidence != null) params.set("has_evidence", String(filters.has_evidence));
      if (filters.only_reviewed) params.set("only_reviewed", "true");
      if (filters.only_unreviewed) params.set("only_unreviewed", "true");
      if (filters.source_id != null) params.set("source_id", String(filters.source_id));
      if (filters.sort_by) params.set("sort_by", filters.sort_by);
      if (filters.sort_order) params.set("sort_order", filters.sort_order);
      if (filters.limit != null) params.set("limit", String(filters.limit));
      if (filters.offset != null) params.set("offset", String(filters.offset));
    }
    const qs = params.toString();
    return req<MatrixResponse>(`/api/matrix${qs ? `?${qs}` : ""}`);
  },
  getMatrixExportUrl: (format: "csv" | "md", filters?: MatrixFilters) => {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.q) params.set("q", filters.q);
      if (filters.tag) filters.tag.forEach((t) => params.append("tag", t));
      if (filters.review_status) params.set("review_status", filters.review_status);
      if (filters.validation_status) params.set("validation_status", filters.validation_status);
    }
    const qs = params.toString();
    return `${BASE}/api/matrix/export.${format}${qs ? `?${qs}` : ""}`;
  },
```

**Step 2: Verify TypeScript compiles**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/frontend
npx tsc --noEmit
```
Expected: no errors

**Step 3: Commit**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/frontend
git add lib/api.ts
git commit -m "feat: add MatrixRow/MatrixResponse types and getMatrix API function"
```

---

## Task 5: Frontend components

**Files:**
- Create: `frontend/components/matrix/StatusBadge.tsx`
- Create: `frontend/components/matrix/MatrixFilters.tsx`
- Create: `frontend/components/matrix/MatrixTable.tsx`
- Create: `frontend/components/matrix/ExportButtons.tsx`

### StatusBadge.tsx

Three badge types: evidence status (validation_status), finding review status, source review status.

```tsx
"use client";

type BadgeVariant = "positive" | "cautious" | "warning" | "neutral";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  positive: "bg-green-100 text-green-800",
  cautious: "bg-yellow-100 text-yellow-800",
  warning: "bg-red-100 text-red-800",
  neutral: "bg-gray-100 text-gray-600",
};

export function ValidationBadge({ status, method }: { status: string | null; method?: string | null }) {
  if (!status) return <span className="text-gray-400 text-xs">—</span>;
  const variant: BadgeVariant =
    status === "evidence_found" ? "positive"
    : status === "evidence_not_found" ? "warning"
    : status === "invalid_page" ? "warning"
    : "neutral";
  const labels: Record<string, string> = {
    evidence_found: "Belegt",
    evidence_not_found: "Nicht belegt",
    no_evidence: "Kein Zitat",
    invalid_page: "Ungültige Seite",
  };
  const label = labels[status] ?? status;
  const methodLabel = method && method !== "none" ? ` (${method})` : "";
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded font-medium ${VARIANT_CLASSES[variant]}`}>
      {label}{methodLabel}
    </span>
  );
}

export function ReviewBadge({ status }: { status: string | null }) {
  if (!status || status === "unreviewed") {
    return <span className="inline-block text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Ungeprüft</span>;
  }
  const variant: BadgeVariant =
    status === "correct" ? "positive"
    : status === "partially_correct" ? "cautious"
    : status === "incorrect" || status === "unsupported" ? "warning"
    : status === "missing_important_context" ? "cautious"
    : "neutral";
  const labels: Record<string, string> = {
    correct: "Korrekt",
    partially_correct: "Teilweise korrekt",
    incorrect: "Falsch",
    unsupported: "Nicht belegt",
    missing_important_context: "Kontext fehlt",
  };
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded font-medium ${VARIANT_CLASSES[variant]}`}>
      {labels[status] ?? status}
    </span>
  );
}
```

### MatrixFilters.tsx

```tsx
"use client";
import { useState } from "react";
import type { MatrixFilters as Filters } from "@/lib/api";

interface Props {
  onSearch: (filters: Filters) => void;
  loading: boolean;
}

export function MatrixFiltersPanel({ onSearch, loading }: Props) {
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [reviewStatus, setReviewStatus] = useState("");
  const [validationStatus, setValidationStatus] = useState("");
  const [onlyUnreviewed, setOnlyUnreviewed] = useState(false);
  const [onlyReviewed, setOnlyReviewed] = useState(false);

  function handleSearch() {
    const filters: Filters = {};
    if (q.trim()) filters.q = q.trim();
    if (tag.trim()) filters.tag = tag.split(",").map((t) => t.trim()).filter(Boolean);
    if (yearFrom) filters.year_from = parseInt(yearFrom, 10);
    if (yearTo) filters.year_to = parseInt(yearTo, 10);
    if (reviewStatus) filters.review_status = reviewStatus;
    if (validationStatus) filters.validation_status = validationStatus;
    if (onlyUnreviewed) filters.only_unreviewed = true;
    if (onlyReviewed) filters.only_reviewed = true;
    onSearch(filters);
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Freitextsuche…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 min-w-48 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Tags (kommagetrennt)"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          className="w-48 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Jahr von"
          value={yearFrom}
          onChange={(e) => setYearFrom(e.target.value)}
          className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Jahr bis"
          value={yearTo}
          onChange={(e) => setYearTo(e.target.value)}
          className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={reviewStatus}
          onChange={(e) => setReviewStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">Alle Review-Status</option>
          <option value="unreviewed">Ungeprüft</option>
          <option value="correct">Korrekt</option>
          <option value="partially_correct">Teilweise korrekt</option>
          <option value="incorrect">Falsch</option>
          <option value="unsupported">Nicht belegt</option>
          <option value="missing_important_context">Kontext fehlt</option>
        </select>
        <select
          value={validationStatus}
          onChange={(e) => setValidationStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">Alle Evidenz-Status</option>
          <option value="evidence_found">Belegt</option>
          <option value="evidence_not_found">Nicht belegt</option>
          <option value="no_evidence">Kein Zitat</option>
          <option value="invalid_page">Ungültige Seite</option>
        </select>
        <label className="flex items-center gap-1 text-sm text-gray-600">
          <input type="checkbox" checked={onlyUnreviewed} onChange={(e) => setOnlyUnreviewed(e.target.checked)} />
          Nur ungeprüft
        </label>
        <label className="flex items-center gap-1 text-sm text-gray-600">
          <input type="checkbox" checked={onlyReviewed} onChange={(e) => setOnlyReviewed(e.target.checked)} />
          Nur geprüft
        </label>
        <button
          onClick={handleSearch}
          disabled={loading}
          className="ml-auto bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Suche…" : "Suchen"}
        </button>
      </div>
    </div>
  );
}
```

### MatrixTable.tsx

```tsx
"use client";
import Link from "next/link";
import type { MatrixRow } from "@/lib/api";
import { ValidationBadge, ReviewBadge } from "./StatusBadge";

interface Props {
  rows: MatrixRow[];
  total: number;
}

function truncate(s: string | null, len = 80): string {
  if (!s) return "—";
  return s.length > len ? s.slice(0, len) + "…" : s;
}

export function MatrixTable({ rows, total }: Props) {
  if (rows.length === 0) {
    return <p className="text-gray-500 text-sm py-8 text-center">Keine Ergebnisse.</p>;
  }

  return (
    <div>
      <p className="text-sm text-gray-500 mb-2">{total} Einträge</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-3 py-2 font-medium text-gray-700">Quelle</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Jahr</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Tags</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Finding (KI-Vorschlag)</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Seiten</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Evidenz-Status</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Review-Status</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Confidence</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Kommentar</th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={`${row.source_id}-${row.finding_id ?? i}`} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2 max-w-48">
                  <div className="font-medium text-gray-900 truncate" title={row.source_title}>
                    {truncate(row.source_title, 40)}
                  </div>
                  <div className="text-xs text-gray-500 truncate">{row.authors || "—"}</div>
                </td>
                <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{row.year ?? "—"}</td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {row.tags.map((t) => (
                      <span key={t} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        {t}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2 max-w-64">
                  {row.finding_statement ? (
                    <span title={row.finding_statement} className="text-gray-800">
                      {truncate(row.finding_statement)}
                    </span>
                  ) : (
                    <span className="text-gray-400 italic">Kein Finding</span>
                  )}
                </td>
                <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                  {row.finding_page_start != null
                    ? row.finding_page_end && row.finding_page_end !== row.finding_page_start
                      ? `${row.finding_page_start}–${row.finding_page_end}`
                      : String(row.finding_page_start)
                    : "—"}
                </td>
                <td className="px-3 py-2">
                  <ValidationBadge status={row.validation_status} method={row.validation_method} />
                </td>
                <td className="px-3 py-2">
                  <ReviewBadge status={row.finding_review_status ?? row.source_review_status} />
                </td>
                <td className="px-3 py-2 text-gray-600">
                  {row.confidence_user != null ? `${row.confidence_user}/5` : "—"}
                </td>
                <td className="px-3 py-2 max-w-40 text-gray-600" title={row.finding_review_comment ?? ""}>
                  {truncate(row.finding_review_comment, 40)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <Link
                    href={`/sources/${row.source_id}`}
                    className="text-indigo-600 hover:underline text-xs mr-2"
                  >
                    Details
                  </Link>
                  <Link
                    href={`/sources/${row.source_id}/review`}
                    className="text-indigo-600 hover:underline text-xs"
                  >
                    Prüfen
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### ExportButtons.tsx

```tsx
"use client";
import type { MatrixFilters } from "@/lib/api";
import { api } from "@/lib/api";

export function ExportButtons({ filters }: { filters: MatrixFilters }) {
  return (
    <div className="flex gap-2">
      <a
        href={api.getMatrixExportUrl("csv", filters)}
        download="matrix_export.csv"
        className="text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-3 py-1.5 hover:border-gray-400"
      >
        CSV
      </a>
      <a
        href={api.getMatrixExportUrl("md", filters)}
        download="matrix_export.md"
        className="text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-3 py-1.5 hover:border-gray-400"
      >
        Markdown
      </a>
    </div>
  );
}
```

**Step 1: Create the component files** (content above for each file)

**Step 2: Verify TypeScript compiles**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/frontend
npx tsc --noEmit
```
Expected: no errors

**Step 3: Commit**

```bash
git add components/matrix/
git commit -m "feat: add matrix components (StatusBadge, MatrixFilters, MatrixTable, ExportButtons)"
```

---

## Task 6: Frontend page + nav update

**Files:**
- Create: `frontend/app/matrix/page.tsx`
- Create: `frontend/app/matrix/MatrixPage.tsx`
- Modify: `frontend/app/layout.tsx`

### page.tsx (Server Component)

```tsx
import { MatrixPage } from "./MatrixPage";

export const dynamic = "force-dynamic";

export default function MatrixRoute() {
  return <MatrixPage />;
}
```

### MatrixPage.tsx (Client Component)

```tsx
"use client";
import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { MatrixRow, MatrixFilters, MatrixResponse } from "@/lib/api";
import { MatrixFiltersPanel } from "@/components/matrix/MatrixFilters";
import { MatrixTable } from "@/components/matrix/MatrixTable";
import { ExportButtons } from "@/components/matrix/ExportButtons";

export function MatrixPage() {
  const [data, setData] = useState<MatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<MatrixFilters>({});

  const handleSearch = useCallback(async (filters: MatrixFilters) => {
    setLoading(true);
    setError(null);
    setActiveFilters(filters);
    try {
      const result = await api.getMatrix(filters);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-semibold text-gray-900">Literatur-Matrix</h1>
        {data && <ExportButtons filters={activeFilters} />}
      </div>

      <MatrixFiltersPanel onSearch={handleSearch} loading={loading} />

      {!data && !loading && (
        <p className="text-gray-500 text-sm text-center py-8">
          Filter setzen und auf „Suchen" klicken.
        </p>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3">
          {error}
        </div>
      )}

      {data && (
        <MatrixTable rows={data.items} total={data.total} />
      )}
    </div>
  );
}
```

### layout.tsx nav update

In `frontend/app/layout.tsx`, add "Matrix" link. The existing nav looks like:

```tsx
<Link href="/sources">Quellen</Link>
<Link href="/upload">Hochladen</Link>
<Link href="/search">Suche</Link>
<Link href="/export">Export</Link>
```

Add after "Export":

```tsx
<Link href="/matrix">Matrix</Link>
```

**Step 1: Create the page files and update layout**

**Step 2: Verify TypeScript compiles**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/frontend
npx tsc --noEmit
```
Expected: no errors

**Step 3: Start dev server and verify in browser**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/frontend
npm run dev
```

Navigate to http://localhost:3000/matrix
- Verify nav shows "Matrix" link
- Verify filter panel renders
- Click "Suchen" → table should appear
- Verify status badges render correctly
- Verify CSV/MD export buttons appear and link to correct URLs

**Step 4: Commit**

```bash
git add app/matrix/ app/layout.tsx
git commit -m "feat: add /matrix route with filter panel, table, and export buttons"
```

---

## Task 7: Final integration run + push

**Step 1: Run full backend test suite**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
python -m pytest tests/ -v
```
Expected: All tests PASS

**Step 2: Run TypeScript check**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/frontend
npx tsc --noEmit
```
Expected: no errors

**Step 3: Verify .env not staged**

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
git status
```
Confirm: `.env` is NOT listed in staged or unstaged files.

**Step 4: Push to GitHub**

```bash
git -C /Users/education/Documents/Literatur/LiteraturKI push origin main
```

---

## Acceptance Checklist

- [ ] `GET /api/matrix` returns `{ items, total, limit, offset, filters_applied }`
- [ ] Each MatrixRow has all 24 fields; sources without findings get `finding_id=null`
- [ ] All 10 filter types work (q, tag, year_from/to, review_status, validation_status, has_evidence, only_reviewed/unreviewed, source_id)
- [ ] Sort by year/title/created_at/updated_at/review_status/validation_status with asc/desc
- [ ] Pagination: limit + offset applied after filtering, total reflects filtered count
- [ ] `GET /api/matrix/export.csv` returns valid CSV with formula injection protection
- [ ] `GET /api/matrix/export.md` returns Markdown grouped by source
- [ ] Frontend /matrix page shows filter panel and "Suchen" button
- [ ] Status badges: correct/evidence_found=green, partially_correct/fragment/fuzzy=yellow, unsupported/not_found=red
- [ ] Export buttons pass current filter state to API URLs
- [ ] Column header "Finding (KI-Vorschlag)" clearly labels AI content
- [ ] Nav shows "Matrix" link
- [ ] All 22 backend tests pass
- [ ] TypeScript compiles without errors
- [ ] `.env` never committed
