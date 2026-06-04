import io
import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a shared connection so all sessions see the same in-memory DB
    from sqlalchemy import StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    # FTS table
    with test_engine.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS document_text_fts USING fts5(text, source_id UNINDEXED, page_number UNINDEXED)"))
        conn.commit()
    Session = sessionmaker(bind=test_engine)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    # Patch the engine used by sources and search modules so FTS indexing and
    # search queries hit the same in-memory DB as the ORM session.
    import app.api.sources as sources_mod
    import app.api.search as search_mod
    monkeypatch.setattr(sources_mod, "engine", test_engine)
    monkeypatch.setattr(search_mod, "engine", test_engine)

    from app import config
    monkeypatch.setattr(config.settings, "upload_dir", str(tmp_path))
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def pdf_bytes():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a test paper about science.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_upload_and_list(client, pdf_bytes):
    r = client.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "paper.pdf"
    assert data["id"] is not None

    r2 = client.get("/api/sources")
    assert len(r2.json()) == 1


def test_get_source_detail(client, pdf_bytes):
    r = client.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})
    source_id = r.json()["id"]

    r2 = client.get(f"/api/sources/{source_id}")
    assert r2.status_code == 200
    detail = r2.json()
    assert len(detail["texts"]) == 1
    assert "science" in detail["texts"][0]["text"]


def test_upload_rejects_non_pdf(client):
    r = client.post("/api/sources/upload", files={"file": ("doc.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_delete_source(client, pdf_bytes):
    r = client.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})
    source_id = r.json()["id"]
    r2 = client.delete(f"/api/sources/{source_id}")
    assert r2.status_code == 200
    r3 = client.get(f"/api/sources/{source_id}")
    assert r3.status_code == 404


def test_add_tag(client, pdf_bytes):
    r = client.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})
    source_id = r.json()["id"]
    r2 = client.post(f"/api/sources/{source_id}/tags", json={"name": "biology"})
    assert r2.status_code == 200
    r3 = client.get(f"/api/sources/{source_id}")
    assert "biology" in r3.json()["tags"]


def test_add_note(client, pdf_bytes):
    r = client.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})
    source_id = r.json()["id"]
    r2 = client.post(f"/api/sources/{source_id}/notes", json={"text": "Important finding!"})
    assert r2.status_code == 200
    r3 = client.get(f"/api/sources/{source_id}")
    assert any(n["text"] == "Important finding!" for n in r3.json()["notes"])


def test_search_endpoint(client, pdf_bytes):
    # Upload a PDF with known text
    client.post("/api/sources/upload", files={"file": ("paper.pdf", pdf_bytes, "application/pdf")})

    # Search for text we know is in the PDF ("science" is in the fixture PDF text)
    r = client.get("/api/search?q=science")
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert results[0]["source_id"] is not None
