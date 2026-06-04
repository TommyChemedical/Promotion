import io
import json
import fitz
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_db
from app.models import Base


MOCK_SUMMARY = {
    "research_question": "Does X cause Y?",
    "methods": "RCT with 200 subjects",
    "data_basis": "Patient records 2020-2023",
    "key_results": [
        {
            "claim": "X causes Y",
            "evidence_text": "We found a significant correlation between X and Y",
            "page_number": 1,
            "confidence": "high",
        }
    ],
    "limitations": "Small sample size",
    "relevance": "Highly relevant to dissertation chapter 3",
    "uncertainty_notes": "",
}


@pytest.fixture
def client_with_source(tmp_path, monkeypatch):
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
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    import app.api.sources as sources_mod
    import app.api.search as search_mod
    monkeypatch.setattr(sources_mod, "engine", engine)
    monkeypatch.setattr(search_mod, "engine", engine)
    from app import config
    monkeypatch.setattr(config.settings, "upload_dir", str(tmp_path))

    # Upload a test PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "X causes Y in clinical trials. We found a significant correlation.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    pdf_bytes = buf.read()

    with TestClient(app) as c:
        r = c.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})
        source_id = r.json()["id"]
        yield c, source_id

    app.dependency_overrides.clear()


def test_summarize_creates_summary(client_with_source):
    client, source_id = client_with_source
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_SUMMARY))]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        r = client.post(f"/api/sources/{source_id}/summarize")
    assert r.status_code == 200
    data = r.json()
    assert data["research_question"] == "Does X cause Y?"
    assert data["model_name"] is not None
    assert data["prompt_version"] == "summary_v1"


def test_summarize_stores_llm_run(client_with_source):
    client, source_id = client_with_source
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_SUMMARY))]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        client.post(f"/api/sources/{source_id}/summarize")
    # Verify summary appears in source detail
    r = client.get(f"/api/sources/{source_id}")
    assert len(r.json()["summaries"]) == 1


def test_summarize_invalid_source(client_with_source):
    client, _ = client_with_source
    r = client.post("/api/sources/99999/summarize")
    assert r.status_code == 404


def test_summarize_handles_malformed_llm_json(client_with_source):
    client, source_id = client_with_source
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="This is not valid JSON at all")]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        r = client.post(f"/api/sources/{source_id}/summarize")
    assert r.status_code == 500
