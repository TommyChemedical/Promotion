import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Source, DocumentText, Summary, Tag, SourceTag, Finding, Note, LLMRun


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_source(db):
    src = Source(title="Test Paper", authors="A. Author", year=2024, filename="test.pdf", file_path="/tmp/test.pdf")
    db.add(src)
    db.commit()
    assert src.id is not None


def test_create_document_text(db):
    src = Source(title="T", filename="t.pdf", file_path="/tmp/t.pdf")
    db.add(src)
    db.commit()
    page = DocumentText(source_id=src.id, page_number=1, text="Hello world")
    db.add(page)
    db.commit()
    assert page.id is not None


def test_create_finding(db):
    src = Source(title="T", filename="t.pdf", file_path="/tmp/t.pdf")
    db.add(src)
    db.commit()
    finding = Finding(
        source_id=src.id,
        claim="X causes Y",
        evidence_text="We found X causes Y on p.3",
        page_number=3,
        confidence="high",
    )
    db.add(finding)
    db.commit()
    assert finding.id is not None


def test_create_llm_run(db):
    src = Source(title="T", filename="t.pdf", file_path="/tmp/t.pdf")
    db.add(src)
    db.commit()
    run = LLMRun(
        source_id=src.id,
        task_type="summarize",
        model_name="claude-sonnet-4-6",
        prompt_version="summary_v1",
        prompt="Summarize this",
        output_json='{"result": "ok"}',
    )
    db.add(run)
    db.commit()
    assert run.id is not None


def test_cascade_delete(db):
    """Deleting a Source should cascade to DocumentText, Finding, Note, LLMRun."""
    src = Source(title="T", filename="t.pdf", file_path="/tmp/t.pdf")
    db.add(src)
    db.commit()
    db.add(DocumentText(source_id=src.id, page_number=1, text="text"))
    db.add(Finding(source_id=src.id, claim="claim", confidence="low"))
    db.commit()
    db.delete(src)
    db.commit()
    assert db.query(DocumentText).count() == 0
    assert db.query(Finding).count() == 0


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
