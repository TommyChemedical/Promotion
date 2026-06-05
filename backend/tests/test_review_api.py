import io
import json
import pytest
import fitz
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


def test_patch_summary_confidence_user_out_of_range(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.patch(
        f"/api/review/summary/{summary_id}",
        json={"review_status": "correct", "confidence_user": 99},
    )
    assert r.status_code == 422


def test_validate_evidence_endpoint(review_client):
    client, source_id, summary_id, finding_id = review_client
    r = client.post(f"/api/review/source/{source_id}/validate-evidence")
    assert r.status_code == 200
    data = r.json()
    assert data["source_id"] == source_id
    assert data["validated"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["finding_id"] == finding_id
    assert data["results"][0]["validation_status"] in (
        "evidence_found", "evidence_not_found", "no_evidence"
    )
