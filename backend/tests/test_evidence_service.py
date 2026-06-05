import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, Finding, DocumentText, Source
from app.services.evidence_service import validate_finding_evidence, ValidationResult


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


def _finding(source_id, quote, page=1):
    return Finding(
        source_id=source_id,
        claim="test claim",
        evidence_quote=quote,
        page_start=page,
    )


def test_no_evidence_quote(db_session):
    session, source_id = db_session
    f = _finding(source_id, "")
    result = validate_finding_evidence(f, session)
    assert result.status == "no_evidence"
    assert result.method == "none"


def test_whitespace_only_quote(db_session):
    session, source_id = db_session
    f = _finding(source_id, "   ")
    result = validate_finding_evidence(f, session)
    assert result.status == "no_evidence"


def test_none_page_returns_invalid_page(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores", page=None)
    result = validate_finding_evidence(f, session)
    assert result.status == "invalid_page"


def test_zero_page_returns_invalid_page(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores", page=0)
    result = validate_finding_evidence(f, session)
    assert result.status == "invalid_page"


def test_missing_page_returns_invalid_page(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores", page=99)
    result = validate_finding_evidence(f, session)
    assert result.status == "invalid_page"


def test_exact_match(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores")
    result = validate_finding_evidence(f, session)
    assert result.status == "evidence_found"
    assert result.method == "exact"
    assert result.score == 1.0


def test_whitespace_normalised(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant  reduction\nin pain  scores")
    result = validate_finding_evidence(f, session)
    assert result.status == "evidence_found"
    assert result.method == "exact"


def test_evidence_not_found(db_session):
    session, source_id = db_session
    f = _finding(source_id, "quantum entanglement disproves gravity completely")
    result = validate_finding_evidence(f, session)
    assert result.status == "evidence_not_found"


def test_validation_result_has_score(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores")
    result = validate_finding_evidence(f, session)
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 1.0


def test_fragment_match(db_session):
    """Two long clauses, both present → fragment match."""
    session, source_id = db_session
    # Both clauses appear in the page text
    quote = "significant reduction in pain scores compared to control, all patients received informed consent"
    f = _finding(source_id, quote)
    result = validate_finding_evidence(f, session)
    assert result.status == "evidence_found"


def test_page_preview_no_evidence_quote(db_session):
    session, source_id = db_session
    from app.services.evidence_service import get_page_preview
    preview = get_page_preview(source_id, 1, session, evidence_quote="", max_len=50)
    assert len(preview) <= 50
    assert preview != ""


def test_page_preview_with_quote(db_session):
    session, source_id = db_session
    from app.services.evidence_service import get_page_preview
    preview = get_page_preview(source_id, 1, session,
                               evidence_quote="significant reduction in pain scores",
                               max_len=300)
    assert "reduction" in preview.lower()


def test_page_preview_none_page(db_session):
    session, source_id = db_session
    from app.services.evidence_service import get_page_preview
    preview = get_page_preview(source_id, None, session)
    assert preview == ""


def test_page_preview_respects_max_len(db_session):
    session, source_id = db_session
    from app.services.evidence_service import get_page_preview
    preview = get_page_preview(source_id, 1, session, max_len=10)
    assert len(preview) <= 10
