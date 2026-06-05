# Review & Validation System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a scientific review and evidence-validation layer so users can rate AI-generated summaries and findings, and so every finding is automatically checked against the extracted page text for citation support.

**Architecture:** All new columns are added to existing SQLite tables via ALTER TABLE in a `_run_migrations()` function in `database.py` (safe for both fresh and existing installs). A new `evidence_service.py` implements pure-Python fuzzy text matching (stdlib only). A new `review.py` router exposes four endpoints. The summarize endpoint auto-validates after creating findings. No schema migration framework is introduced—the project already uses `create_all` + raw SQL patching.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, SQLite, difflib (stdlib), pytest

---

## Task 1: Extend Data Models + DB Migration

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_models.py`

### Step 1: Write the failing test

Add to `backend/tests/test_models.py`:

```python
def test_finding_has_review_and_evidence_columns():
    from sqlalchemy import inspect, create_engine
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("findings")}
    for col in ("evidence_quote", "validation_status", "review_status",
                "review_comment", "reviewed_at", "reviewed_by",
                "confidence_user", "page_end"):
        assert col in cols, f"Missing column: {col}"


def test_summary_has_review_columns():
    from sqlalchemy import inspect, create_engine
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("summaries")}
    for col in ("review_status", "review_comment", "reviewed_at",
                "reviewed_by", "confidence_user"):
        assert col in cols, f"Missing column: {col}"
```

### Step 2: Run to verify failure

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_models.py::test_finding_has_review_and_evidence_columns -v --tb=short 2>&1 | tail -10
```

Expected: FAILED (columns missing)

### Step 3: Extend `backend/app/models.py`

Replace the `Finding` class (keep all existing fields, add new ones at the end):

```python
class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    claim = Column(Text, nullable=False)
    evidence_text = Column(Text, default="")
    evidence_quote = Column(Text, default="")        # verbatim quote from source text
    page_number = Column(Integer, nullable=True)      # primary page reference
    page_end = Column(Integer, nullable=True)         # end page for multi-page evidence
    relevance = Column(Text, default="")
    confidence = Column(String, default="low")        # AI confidence: low | medium | high
    validation_status = Column(String, default="no_evidence")  # no_evidence | evidence_found | evidence_not_found
    review_status = Column(String, default="unreviewed")
    review_comment = Column(Text, default="")
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, default="local_user")
    confidence_user = Column(Integer, nullable=True)  # user rating 1–5
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="findings")
```

Replace the `Summary` class (keep all existing fields, add review fields at the end):

```python
class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    model_name = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    research_question = Column(Text, default="")
    methods = Column(Text, default="")
    data_basis = Column(Text, default="")
    key_results = Column(Text, default="[]")
    limitations = Column(Text, default="")
    relevance = Column(Text, default="")
    uncertainty_notes = Column(Text, default="")
    review_status = Column(String, default="unreviewed")
    review_comment = Column(Text, default="")
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, default="local_user")
    confidence_user = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="summaries")
```

### Step 4: Add `_run_migrations()` to `backend/app/database.py`

After the existing `_create_fts_table()` function, add:

```python
def _run_migrations():
    """Add new columns to existing tables. Safe to run on fresh and existing DBs."""
    new_columns = [
        ("findings", "evidence_quote TEXT NOT NULL DEFAULT ''"),
        ("findings", "page_end INTEGER"),
        ("findings", "validation_status TEXT NOT NULL DEFAULT 'no_evidence'"),
        ("findings", "review_status TEXT NOT NULL DEFAULT 'unreviewed'"),
        ("findings", "review_comment TEXT NOT NULL DEFAULT ''"),
        ("findings", "reviewed_at DATETIME"),
        ("findings", "reviewed_by TEXT NOT NULL DEFAULT 'local_user'"),
        ("findings", "confidence_user INTEGER"),
        ("summaries", "review_status TEXT NOT NULL DEFAULT 'unreviewed'"),
        ("summaries", "review_comment TEXT NOT NULL DEFAULT ''"),
        ("summaries", "reviewed_at DATETIME"),
        ("summaries", "reviewed_by TEXT NOT NULL DEFAULT 'local_user'"),
        ("summaries", "confidence_user INTEGER"),
    ]
    with engine.connect() as conn:
        for table, col_def in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
            except Exception:
                pass  # column already exists (fresh install via create_all)
        conn.commit()
```

Then update `init_db()` to call it:

```python
def init_db():
    Base.metadata.create_all(bind=engine)
    _create_fts_table()
    _run_migrations()
```

### Step 5: Run all tests

```bash
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: all existing tests still pass + 2 new tests pass

### Step 6: Commit

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/models.py backend/app/database.py backend/tests/test_models.py
git commit -m "feat: add review and evidence validation columns to Finding and Summary"
```

---

## Task 2: Evidence Validation Service

**Files:**
- Create: `backend/app/services/evidence_service.py`
- Create: `backend/tests/test_evidence_service.py`

### Step 1: Write the failing tests

Create `backend/tests/test_evidence_service.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, Finding, DocumentText, Source
from app.services.evidence_service import validate_finding_evidence


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        source = Source(title="Test", filename="t.pdf", file_path="/tmp/t.pdf")
        session.add(source)
        session.flush()
        page = DocumentText(
            source_id=source.id,
            page_number=1,
            text="The treatment group showed a significant reduction in pain scores "
                 "compared to control (p < 0.001). All patients received informed consent.",
        )
        session.add(page)
        session.commit()
        yield session, source.id


def _finding(source_id, quote, page=1, page_end=None):
    return Finding(
        source_id=source_id,
        claim="test claim",
        evidence_quote=quote,
        page_number=page,
        page_end=page_end,
    )


def test_no_evidence_quote(db_session):
    session, source_id = db_session
    f = _finding(source_id, "")
    assert validate_finding_evidence(f, session) == "no_evidence"


def test_exact_match(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores")
    assert validate_finding_evidence(f, session) == "evidence_found"


def test_whitespace_normalised(db_session):
    session, source_id = db_session
    # extra spaces, mixed case, newline
    f = _finding(source_id, "significant  reduction\nin pain  scores")
    assert validate_finding_evidence(f, session) == "evidence_found"


def test_fuzzy_word_overlap(db_session):
    session, source_id = db_session
    # 4 of 5 words match (80 % overlap) — should still be found
    f = _finding(source_id, "significant reduction pain scores patients")
    assert validate_finding_evidence(f, session) == "evidence_found"


def test_evidence_not_found(db_session):
    session, source_id = db_session
    f = _finding(source_id, "quantum entanglement disproves gravity completely")
    assert validate_finding_evidence(f, session) == "evidence_not_found"


def test_wrong_page_number(db_session):
    session, source_id = db_session
    # page 99 does not exist
    f = _finding(source_id, "significant reduction in pain scores", page=99)
    assert validate_finding_evidence(f, session) == "evidence_not_found"


def test_none_page_number(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores", page=None)
    assert validate_finding_evidence(f, session) == "evidence_not_found"
```

### Step 2: Run to verify failure

```bash
PYTHONPATH=. pytest tests/test_evidence_service.py -v --tb=short 2>&1 | tail -10
```

Expected: ImportError / ModuleNotFoundError

### Step 3: Create `backend/app/services/evidence_service.py`

```python
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
    Check whether finding.evidence_quote can be found in the extracted page text.

    Returns:
        "no_evidence"         – evidence_quote is empty
        "evidence_found"      – exact or fuzzy match in page text
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


def get_page_preview(source_id: int, page_number: int | None, db: Session,
                     evidence_quote: str = "", max_len: int = 300) -> str:
    """Return a short excerpt of the page text, centred on the evidence quote if possible."""
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
```

### Step 4: Run tests

```bash
PYTHONPATH=. pytest tests/test_evidence_service.py -v --tb=short 2>&1 | tail -15
```

Expected: 7 passed

### Step 5: Run all tests

```bash
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: all pass

### Step 6: Commit

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/services/evidence_service.py backend/tests/test_evidence_service.py
git commit -m "feat: evidence validation service with exact and fuzzy text matching"
```

---

## Task 3: Review Schemas

**Files:**
- Modify: `backend/app/schemas.py`

No standalone test needed — schemas are exercised by the API tests in Task 4. The models test already confirms the DB columns exist.

### Step 1: Add to `backend/app/schemas.py`

Append at the end of the file (keep all existing schemas unchanged):

```python
from enum import Enum
from typing import Optional


class ReviewStatus(str, Enum):
    unreviewed = "unreviewed"
    correct = "correct"
    partially_correct = "partially_correct"
    incorrect = "incorrect"
    unsupported = "unsupported"
    missing_important_context = "missing_important_context"


class ValidationStatus(str, Enum):
    no_evidence = "no_evidence"
    evidence_found = "evidence_found"
    evidence_not_found = "evidence_not_found"


class ReviewUpdateRequest(BaseModel):
    review_status: ReviewStatus
    review_comment: str = ""
    confidence_user: Optional[int] = None  # 1–5


class ReviewableSummaryResponse(BaseModel):
    id: int
    research_question: str
    methods: str
    data_basis: str
    limitations: str
    relevance: str
    uncertainty_notes: str
    review_status: ReviewStatus
    review_comment: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: str
    confidence_user: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewableFindingResponse(BaseModel):
    id: int
    claim: str
    evidence_text: str
    evidence_quote: str
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    confidence: str
    validation_status: ValidationStatus
    review_status: ReviewStatus
    review_comment: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: str
    confidence_user: Optional[int] = None
    page_preview: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceReviewResponse(BaseModel):
    source_id: int
    summary: Optional[ReviewableSummaryResponse] = None
    findings: list[ReviewableFindingResponse] = []


class EvidenceValidationResult(BaseModel):
    finding_id: int
    validation_status: ValidationStatus


class EvidenceValidationResponse(BaseModel):
    source_id: int
    validated: int
    results: list[EvidenceValidationResult]
```

Also update `FindingCreate` to accept the new fields so manual findings can include evidence:

```python
class FindingCreate(BaseModel):
    claim: str
    evidence_text: str = ""
    evidence_quote: str = ""
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    relevance: str = ""
    confidence: str = "low"
```

And update `FindingRead` to expose the new fields:

```python
class FindingRead(BaseModel):
    id: int
    claim: str
    evidence_text: str
    evidence_quote: str
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    relevance: str
    confidence: str
    validation_status: str
    review_status: str
    review_comment: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: str
    confidence_user: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
```

### Step 2: Run tests to confirm nothing broke

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: all pass (schemas have no side effects until used)

### Step 3: Commit

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/schemas.py
git commit -m "feat: review and validation schemas (ReviewStatus, ValidationStatus, review responses)"
```

---

## Task 4: Review API Router

**Files:**
- Create: `backend/app/api/review.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_review_api.py`

### Step 1: Write the failing tests

Create `backend/tests/test_review_api.py`:

```python
import io
import json
import pytest
import fitz
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import Base, Source, DocumentText, Summary, Finding


@pytest.fixture
def review_client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_text_fts "
            "USING fts5(text, source_id UNINDEXED, page_number UNINDEXED)"
        ))
        conn.commit()
    Session = sessionmaker(bind=engine)

    def override_db():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override_db

    import app.api.sources as sources_mod
    import app.api.search as search_mod
    monkeypatch.setattr(sources_mod, "engine", engine)
    monkeypatch.setattr(search_mod, "engine", engine)
    from app import config
    monkeypatch.setattr(config.settings, "upload_dir", str(tmp_path))

    # Insert test data directly
    with Session() as session:
        source = Source(title="Test Paper", filename="t.pdf", file_path="/tmp/t.pdf")
        session.add(source)
        session.flush()

        page = DocumentText(
            source_id=source.id, page_number=1,
            text="Treatment significantly reduced pain scores compared to placebo (p < 0.001).",
        )
        session.add(page)

        summary = Summary(
            source_id=source.id, model_name="test", prompt_version="v1",
            research_question="Does treatment reduce pain?",
            methods="RCT", data_basis="100 patients",
            key_results="[]", limitations="", relevance="", uncertainty_notes="",
        )
        session.add(summary)
        session.flush()

        finding = Finding(
            source_id=source.id,
            claim="Treatment reduces pain",
            evidence_text="significant reduction in pain",
            evidence_quote="significantly reduced pain scores",
            page_number=1,
            confidence="high",
            validation_status="evidence_found",
        )
        session.add(finding)
        session.commit()

        source_id = source.id
        summary_id = summary.id
        finding_id = finding.id

    with TestClient(app) as c:
        yield c, source_id, summary_id, finding_id

    app.dependency_overrides.clear()


def test_get_source_review_response(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.get(f"/api/review/sources/{source_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["source_id"] == source_id
    assert data["summary"] is not None
    assert data["summary"]["research_question"] == "Does treatment reduce pain?"
    assert data["summary"]["review_status"] == "unreviewed"
    assert len(data["findings"]) == 1
    f = data["findings"][0]
    assert f["claim"] == "Treatment reduces pain"
    assert f["validation_status"] == "evidence_found"
    assert "page_preview" in f


def test_get_source_review_404(review_client):
    client, *_ = review_client
    r = client.get("/api/review/sources/9999")
    assert r.status_code == 404


def test_patch_summary_review_status(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.patch(
        f"/api/review/summary/{summary_id}",
        json={"review_status": "correct", "review_comment": "Looks good", "confidence_user": 4},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["review_status"] == "correct"
    assert data["review_comment"] == "Looks good"
    assert data["confidence_user"] == 4
    assert data["reviewed_at"] is not None


def test_patch_summary_invalid_status(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.patch(
        f"/api/review/summary/{summary_id}",
        json={"review_status": "totally_made_up"},
    )
    assert r.status_code == 422


def test_patch_finding_review_status(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.patch(
        f"/api/review/finding/{finding_id}",
        json={"review_status": "unsupported", "review_comment": "No direct quote"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["review_status"] == "unsupported"
    assert data["review_comment"] == "No direct quote"


def test_validate_evidence_endpoint(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.post(f"/api/review/source/{source_id}/validate-evidence")
    assert r.status_code == 200
    data = r.json()
    assert data["source_id"] == source_id
    assert data["validated"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["finding_id"] == finding_id
    assert data["results"][0]["validation_status"] in ("evidence_found", "evidence_not_found", "no_evidence")
```

### Step 2: Run to verify failure

```bash
PYTHONPATH=. pytest tests/test_review_api.py -v --tb=short 2>&1 | tail -10
```

Expected: 404 Not Found errors (router not registered yet)

### Step 3: Create `backend/app/api/review.py`

```python
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Source, Summary, Finding
from app.schemas import (
    ReviewUpdateRequest, ReviewableSummaryResponse, ReviewableFindingResponse,
    SourceReviewResponse, EvidenceValidationResponse, EvidenceValidationResult,
    ValidationStatus,
)
from app.services.evidence_service import validate_finding_evidence, get_page_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/sources/{source_id}", response_model=SourceReviewResponse)
def get_source_review(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")

    summary = db.query(Summary).filter_by(source_id=source_id).order_by(Summary.created_at.desc()).first()
    findings = db.query(Finding).filter_by(source_id=source_id).order_by(Finding.id).all()

    summary_resp = None
    if summary:
        summary_resp = ReviewableSummaryResponse.model_validate(summary)

    finding_resps = []
    for f in findings:
        preview = get_page_preview(source_id, f.page_number, db, f.evidence_quote or "")
        resp = ReviewableFindingResponse(
            id=f.id,
            claim=f.claim,
            evidence_text=f.evidence_text or "",
            evidence_quote=f.evidence_quote or "",
            page_number=f.page_number,
            page_end=f.page_end,
            confidence=f.confidence or "low",
            validation_status=ValidationStatus(f.validation_status or "no_evidence"),
            review_status=f.review_status or "unreviewed",
            review_comment=f.review_comment or "",
            reviewed_at=f.reviewed_at,
            reviewed_by=f.reviewed_by or "local_user",
            confidence_user=f.confidence_user,
            page_preview=preview,
            created_at=f.created_at,
        )
        finding_resps.append(resp)

    return SourceReviewResponse(
        source_id=source_id,
        summary=summary_resp,
        findings=finding_resps,
    )


@router.patch("/summary/{summary_id}", response_model=ReviewableSummaryResponse)
def patch_summary_review(summary_id: int, body: ReviewUpdateRequest, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(404, "Zusammenfassung nicht gefunden")

    summary.review_status = body.review_status.value
    summary.review_comment = body.review_comment
    summary.confidence_user = body.confidence_user
    summary.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(summary)
    return ReviewableSummaryResponse.model_validate(summary)


@router.patch("/finding/{finding_id}", response_model=ReviewableFindingResponse)
def patch_finding_review(finding_id: int, body: ReviewUpdateRequest, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(404, "Finding nicht gefunden")

    finding.review_status = body.review_status.value
    finding.review_comment = body.review_comment
    finding.confidence_user = body.confidence_user
    finding.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(finding)

    preview = get_page_preview(finding.source_id, finding.page_number, db, finding.evidence_quote or "")
    return ReviewableFindingResponse(
        id=finding.id,
        claim=finding.claim,
        evidence_text=finding.evidence_text or "",
        evidence_quote=finding.evidence_quote or "",
        page_number=finding.page_number,
        page_end=finding.page_end,
        confidence=finding.confidence or "low",
        validation_status=ValidationStatus(finding.validation_status or "no_evidence"),
        review_status=finding.review_status or "unreviewed",
        review_comment=finding.review_comment or "",
        reviewed_at=finding.reviewed_at,
        reviewed_by=finding.reviewed_by or "local_user",
        confidence_user=finding.confidence_user,
        page_preview=preview,
        created_at=finding.created_at,
    )


@router.post("/source/{source_id}/validate-evidence", response_model=EvidenceValidationResponse)
def validate_all_evidence(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")

    findings = db.query(Finding).filter_by(source_id=source_id).all()
    results = []
    for f in findings:
        status = validate_finding_evidence(f, db)
        f.validation_status = status
        results.append(EvidenceValidationResult(
            finding_id=f.id,
            validation_status=ValidationStatus(status),
        ))

    db.commit()
    logger.info("Source %d: validated evidence for %d finding(s)", source_id, len(findings))

    return EvidenceValidationResponse(
        source_id=source_id,
        validated=len(findings),
        results=results,
    )
```

### Step 4: Register router in `backend/app/main.py`

Add these two lines (imports + include):

```python
# Add to imports at top:
from app.api import review as review_router

# Add after the existing include_router calls:
app.include_router(review_router.router)
```

Full updated `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import sources as sources_router
from app.api import search as search_router
from app.api import summarize as summarize_router
from app.api import export as export_router
from app.api import review as review_router

app = FastAPI(title="LiteraturKI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router.router)
app.include_router(search_router.router)
app.include_router(summarize_router.router)
app.include_router(export_router.router)
app.include_router(review_router.router)


@app.on_event("startup")
def startup():
    from app.database import init_db
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

### Step 5: Run tests

```bash
PYTHONPATH=. pytest tests/test_review_api.py -v --tb=short 2>&1 | tail -15
```

Expected: all 6 tests pass

### Step 6: Run all tests

```bash
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: all pass

### Step 7: Commit

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/api/review.py backend/app/main.py backend/tests/test_review_api.py
git commit -m "feat: review API endpoints (GET source review, PATCH summary/finding, POST validate-evidence)"
```

---

## Task 5: Auto-Validate Findings After Summarize + Update Prompt

**Files:**
- Modify: `backend/app/prompts/summary_v1.md`
- Modify: `backend/app/api/summarize.py`
- Modify: `backend/tests/test_summarize_api.py`

### Step 1: Write the failing test

Add to `backend/tests/test_summarize_api.py`:

```python
def test_summarize_auto_validates_evidence(client_with_source):
    """After summarization, each finding must have a validation_status set."""
    client, source_id, Session = client_with_source
    mock_summary_with_quote = {
        "research_question": "Does X reduce pain?",
        "methods": "RCT", "data_basis": "100 patients",
        "key_results": [
            {
                "claim": "X reduces pain",
                "evidence_text": "Significant reduction found",
                "evidence_quote": "X causes Y in clinical trials",
                "page_number": 1,
                "confidence": "high",
            }
        ],
        "limitations": "", "relevance": "", "uncertainty_notes": "",
    }
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(mock_summary_with_quote))]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        r = client.post(f"/api/sources/{source_id}/summarize")
    assert r.status_code == 200
    with Session() as session:
        from app.models import Finding
        findings = session.query(Finding).filter_by(source_id=source_id).all()
    assert len(findings) == 1
    # validation_status must be set (not None) — exact value depends on page text
    assert findings[0].validation_status in ("evidence_found", "evidence_not_found", "no_evidence")
```

### Step 2: Run to verify failure

```bash
PYTHONPATH=. pytest tests/test_summarize_api.py::test_summarize_auto_validates_evidence -v --tb=short 2>&1 | tail -10
```

Expected: FAILED (validation_status is "no_evidence" because evidence_quote not used)

### Step 3: Update `backend/app/prompts/summary_v1.md`

Add `evidence_quote` to the key_results output format:

```markdown
Du bist ein wissenschaftlicher Assistent. Analysiere den folgenden Text aus einer wissenschaftlichen Publikation und gib eine strukturierte JSON-Zusammenfassung zurück.

**Regeln:**
- Jede Aussage muss mit einer Textstelle aus dem Quellentext belegt sein.
- Wenn keine belegende Textstelle gefunden wird, setze `confidence` auf `low`.
- Erfinde keine Inhalte. Markiere Unsicherheiten explizit.
- Trenne belegte Aussagen von Interpretationen.
- Antworte ausschließlich mit validem JSON. Kein Text davor oder danach. Keine Markdown-Code-Blöcke.
- `evidence_quote` muss ein wörtliches Zitat aus dem Quellentext sein. Falls kein direktes Zitat verfügbar, leeres Feld lassen.

**Ausgabeformat (nur dieses JSON, nichts anderes):**

{
  "research_question": "...",
  "methods": "...",
  "data_basis": "...",
  "key_results": [
    {
      "claim": "...",
      "evidence_text": "Beschreibung, warum diese Textstelle die Aussage belegt",
      "evidence_quote": "wörtliches Zitat aus dem Quellentext",
      "page_number": null,
      "confidence": "low|medium|high"
    }
  ],
  "limitations": "...",
  "relevance": "...",
  "uncertainty_notes": "..."
}

**Text der Quelle:**

{text}
```

### Step 4: Update `backend/app/api/summarize.py`

Add the import for evidence validation and call it after creating each Finding.

Add to imports:
```python
from app.services.evidence_service import validate_finding_evidence
```

Update the Finding creation loop (replace the existing loop at the bottom of `summarize_source`):

```python
    # Auto-create Finding records from key_results and validate evidence
    for kr in merged.get("key_results", []):
        if not kr.get("claim"):
            continue
        finding = Finding(
            source_id=source_id,
            claim=kr.get("claim", ""),
            evidence_text=kr.get("evidence_text", ""),
            evidence_quote=kr.get("evidence_quote", ""),
            page_number=kr.get("page_number"),
            confidence=kr.get("confidence", "low"),
        )
        db.add(finding)
        db.flush()  # get finding.id before validation
        finding.validation_status = validate_finding_evidence(finding, db)
```

The `db.flush()` is needed so the Finding has a proper `source_id` set before the validation query runs against `DocumentText`.

### Step 5: Run tests

```bash
PYTHONPATH=. pytest tests/test_summarize_api.py -v --tb=short 2>&1 | tail -15
```

Expected: all summarize tests pass including the new one

The test `test_summarize_auto_validates_evidence` uploaded a single-page PDF with text "X causes Y in clinical trials. We found a significant correlation." and the mock returns `evidence_quote: "X causes Y in clinical trials"` → `evidence_found`.

### Step 6: Run all tests

```bash
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: all pass

### Step 7: Commit

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add backend/app/prompts/summary_v1.md backend/app/api/summarize.py backend/tests/test_summarize_api.py
git commit -m "feat: auto-validate finding evidence after summarize, add evidence_quote to prompt"
```

---

## Task 6: Update README

**Files:**
- Modify: `README.md`

### Step 1: Read the current README

```bash
cat /Users/education/Documents/Literatur/LiteraturKI/README.md
```

### Step 2: Add a "Review & Validation" section

Append the following to the README (after the existing content, before any footer):

```markdown
## Review & Validation System

### Review Status Values

Each Summary and Finding has a `review_status` field set by the user via the review API:

| Status | Bedeutung |
|--------|-----------|
| `unreviewed` | Noch nicht manuell geprüft (Standard) |
| `correct` | Inhalt korrekt und vollständig belegt |
| `partially_correct` | Teilweise korrekt, aber Einschränkungen |
| `incorrect` | Inhaltlich falsch |
| `unsupported` | Keine ausreichende Belegstelle vorhanden |
| `missing_important_context` | Korrekt, aber wichtiger Kontext fehlt |

### Evidence Validation

When a finding is created from a summary (automatic) or manually added, the system checks whether the `evidence_quote` appears in the extracted PDF page text.

**Algorithm:**
1. If `evidence_quote` is empty → `no_evidence`
2. Look up `DocumentText` for the given `page_number`
3. If page not found → `evidence_not_found`
4. Normalize whitespace (lowercase, collapse spaces/newlines)
5. Check exact substring match
6. If no exact match: check word overlap (≥ 75% of quote words appear in page text)
7. Match found → `evidence_found`, no match → `evidence_not_found`

**Validation Status Values:**

| Status | Bedeutung |
|--------|-----------|
| `no_evidence` | Kein Zitat angegeben — Finding kann nicht automatisch geprüft werden |
| `evidence_found` | Zitat im extrahierten Seitentext gefunden (exakt oder fuzzy) |
| `evidence_not_found` | Zitat konnte im angegebenen Seitentext nicht gefunden werden |

### Why Findings Without Evidence Are Not Automatically Rejected

Findings with `no_evidence` or `evidence_not_found` are **preserved and visible** because:

- OCR quality may be imperfect — a quote may not match even if the source is correct
- The LLM may paraphrase rather than quote verbatim
- Multi-page evidence cannot always be captured in a single quote
- The user must make the final scientific judgement

These findings are flagged as unverified (`review_status: unreviewed` + `validation_status: no_evidence/evidence_not_found`) and must be manually reviewed before being treated as established findings.

### Limits of Automatic Checking

- The fuzzy matcher uses word overlap — it does not understand semantic meaning
- Evidence spread across multiple pages may not be fully captured
- Tables and figures cannot be validated through text matching
- The LLM may cite the wrong page number — always verify manually for critical claims

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/review/sources/{id}` | Full review view: summary + findings with page previews |
| `PATCH` | `/api/review/summary/{id}` | Set review_status, comment, confidence_user |
| `PATCH` | `/api/review/finding/{id}` | Set review_status, comment, confidence_user |
| `POST` | `/api/review/source/{id}/validate-evidence` | Re-run evidence validation for all findings |
```

### Step 3: Run all tests one final time

```bash
cd /Users/education/Documents/Literatur/LiteraturKI/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: all pass

### Step 4: Commit + push

```bash
cd /Users/education/Documents/Literatur/LiteraturKI
git add README.md
git commit -m "docs: document review status values, evidence validation, and API endpoints"
git push
```

---

## Execution Checklist

- [ ] Task 1: Extend models + DB migration
- [ ] Task 2: Evidence validation service
- [ ] Task 3: Review schemas
- [ ] Task 4: Review API router + register in main.py
- [ ] Task 5: Auto-validate findings after summarize + update prompt
- [ ] Task 6: Update README + push
