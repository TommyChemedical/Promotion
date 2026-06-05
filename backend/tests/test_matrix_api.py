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

        src2 = Source(title="Beta Paper", authors="Jones A", year=2021,
                      filename="b.pdf", file_path="/b.pdf", doi="", journal="")
        session.add(src2)
        session.commit()
        yield session


def test_build_matrix_rows_with_finding(matrix_db):
    rows = build_matrix_rows(matrix_db)
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
    assert all(r.year is not None and r.year >= 2022 for r in filtered)


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
    assert all(
        r.source_review_status == "unreviewed"
        and r.finding_review_status in (None, "unreviewed")
        for r in filtered
    )


def test_filter_by_source_id(matrix_db):
    rows = build_matrix_rows(matrix_db)
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
