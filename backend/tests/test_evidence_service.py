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


def _finding(source_id, quote, page=1):
    return Finding(
        source_id=source_id,
        claim="test claim",
        evidence_quote=quote,
        page_number=page,
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
    f = _finding(source_id, "significant  reduction\nin pain  scores")
    assert validate_finding_evidence(f, session) == "evidence_found"


def test_fuzzy_word_overlap(db_session):
    session, source_id = db_session
    # 4 of 5 words match (80% overlap) — should still be found
    f = _finding(source_id, "significant reduction pain scores patients")
    assert validate_finding_evidence(f, session) == "evidence_found"


def test_evidence_not_found(db_session):
    session, source_id = db_session
    f = _finding(source_id, "quantum entanglement disproves gravity completely")
    assert validate_finding_evidence(f, session) == "evidence_not_found"


def test_wrong_page_number(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores", page=99)
    assert validate_finding_evidence(f, session) == "evidence_not_found"


def test_none_page_number(db_session):
    session, source_id = db_session
    f = _finding(source_id, "significant reduction in pain scores", page=None)
    assert validate_finding_evidence(f, session) == "evidence_not_found"
