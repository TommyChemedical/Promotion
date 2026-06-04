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
from app.models import Base, LLMRun


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
        yield c, source_id, Session

    app.dependency_overrides.clear()


def test_summarize_creates_summary(client_with_source):
    client, source_id, _ = client_with_source
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
    client, source_id, Session = client_with_source
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_SUMMARY))]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        r = client.post(f"/api/sources/{source_id}/summarize")
    assert r.status_code == 200
    # Verify at least one LLMRun with task_type="summarize" was stored
    with Session() as session:
        llm_runs = (
            session.query(LLMRun)
            .filter_by(source_id=source_id, task_type="summarize")
            .all()
        )
    assert len(llm_runs) >= 1


def test_summarize_invalid_source(client_with_source):
    client, _, _s = client_with_source
    r = client.post("/api/sources/99999/summarize")
    assert r.status_code == 404


def test_summarize_handles_malformed_llm_json(client_with_source):
    client, source_id, _ = client_with_source
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="This is not valid JSON at all")]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        r = client.post(f"/api/sources/{source_id}/summarize")
    assert r.status_code == 500


def test_summarize_uses_all_chunks_for_long_paper(client_with_source):
    """When CHUNK_SIZE is patched small, LLM is called once per chunk and results are merged."""
    client, _single_page_source_id, _ = client_with_source

    # Build a two-page PDF so that with a tiny CHUNK_SIZE each page becomes its own chunk.
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Page one text: X causes Y in clinical trials.")
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Page two text: additional findings about Z.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    r_upload = client.post(
        "/api/sources/upload",
        files={"file": ("long_paper.pdf", buf.read(), "application/pdf")},
    )
    assert r_upload.status_code == 200
    source_id = r_upload.json()["id"]

    call_results = [
        {
            "research_question": "RQ from chunk 1",
            "methods": "RCT", "data_basis": "100 patients",
            "key_results": [{"claim": "Finding A", "evidence_text": "text A", "page_number": 1, "confidence": "high"}],
            "limitations": "small sample", "relevance": "high", "uncertainty_notes": "",
        },
        {
            "research_question": "RQ from chunk 2",
            "methods": "RCT", "data_basis": "100 patients",
            "key_results": [{"claim": "Finding B", "evidence_text": "text B", "page_number": 2, "confidence": "medium"}],
            "limitations": "small sample", "relevance": "high", "uncertainty_notes": "",
        },
    ]
    call_index = 0

    def side_effect(**kwargs):
        nonlocal call_index
        result = call_results[call_index % len(call_results)]
        call_index += 1
        msg = MagicMock()
        msg.content = [MagicMock(text=json.dumps(result))]
        return msg

    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.side_effect = side_effect
        import app.api.summarize as summarize_mod
        original_chunk = summarize_mod.CHUNK_SIZE
        summarize_mod.CHUNK_SIZE = 5  # force every page into its own chunk
        try:
            r = client.post(f"/api/sources/{source_id}/summarize")
        finally:
            summarize_mod.CHUNK_SIZE = original_chunk

    assert r.status_code == 200
    data = r.json()
    # research_question comes from first chunk
    assert data["research_question"] == "RQ from chunk 1"
    # key_results merged from all chunks
    results = json.loads(data["key_results"])
    assert any(kr["claim"] == "Finding A" for kr in results)
    # findings from chunk 2 must also be present in the merged results
    assert any(kr["claim"] == "Finding B" for kr in results)


def test_summarize_auto_creates_findings(client_with_source):
    """After summarization, Finding records should be auto-created from key_results."""
    client, source_id, _ = client_with_source
    mock_summary = {
        "research_question": "Does X cause Y?",
        "methods": "RCT", "data_basis": "200 subjects",
        "key_results": [
            {"claim": "X causes Y", "evidence_text": "We found...", "page_number": 1, "confidence": "high"},
            {"claim": "Y increases Z", "evidence_text": "Z rose by 10%", "page_number": 2, "confidence": "medium"},
        ],
        "limitations": "small", "relevance": "high", "uncertainty_notes": "",
    }
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(mock_summary))]
    with patch("app.services.llm_service.llm_service._client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        client.post(f"/api/sources/{source_id}/summarize")

    r = client.get(f"/api/sources/{source_id}")
    assert r.status_code == 200
    findings = r.json()["findings"]
    assert len(findings) == 2
    claims = [f["claim"] for f in findings]
    assert "X causes Y" in claims
    assert "Y increases Z" in claims
