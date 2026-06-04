import io
import fitz
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, Source, DocumentText
from app.services.search_service import index_document_text, search_fulltext


@pytest.fixture
def db_engine():
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
    return engine


@pytest.fixture
def db_with_indexed_source(db_engine):
    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        src = Source(title="Test Paper", filename="t.pdf", file_path="/tmp/t.pdf")
        db.add(src)
        db.flush()
        dt = DocumentText(source_id=src.id, page_number=1, text="Photosynthesis occurs in chloroplasts of plant cells")
        db.add(dt)
        db.commit()
        index_document_text(db_engine, dt.id, dt.text, src.id, dt.page_number)
        yield db_engine, src.id


def test_search_finds_indexed_text(db_with_indexed_source):
    engine, source_id = db_with_indexed_source
    results = search_fulltext(engine, "photosynthesis")
    assert len(results) == 1
    assert results[0]["source_id"] == source_id
    assert results[0]["page_number"] == 1
    assert "snippet" in results[0]


def test_search_case_insensitive(db_with_indexed_source):
    engine, source_id = db_with_indexed_source
    results = search_fulltext(engine, "CHLOROPLASTS")
    assert len(results) == 1


def test_search_returns_empty_for_no_match(db_with_indexed_source):
    engine, _ = db_with_indexed_source
    results = search_fulltext(engine, "quantumcomputing")
    assert results == []


def test_delete_removes_fts_entries(db_with_indexed_source):
    engine, source_id = db_with_indexed_source
    # Verify it's indexed
    results = search_fulltext(engine, "photosynthesis")
    assert len(results) == 1

    # Delete from FTS
    from sqlalchemy import text as sql_text
    with engine.connect() as conn:
        conn.execute(sql_text("DELETE FROM document_text_fts WHERE source_id = :sid"), {"sid": source_id})
        conn.commit()

    # Should not find it anymore
    results = search_fulltext(engine, "photosynthesis")
    assert results == []


def test_index_multiple_pages(db_engine):
    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        src = Source(title="Multi-Page", filename="m.pdf", file_path="/tmp/m.pdf")
        db.add(src)
        db.flush()
        for i, text_content in enumerate(["alpha content", "beta content", "gamma content"], 1):
            dt = DocumentText(source_id=src.id, page_number=i, text=text_content)
            db.add(dt)
            db.flush()
            index_document_text(db_engine, dt.id, text_content, src.id, i)
        db.commit()

    results = search_fulltext(db_engine, "beta")
    assert len(results) == 1
    assert results[0]["page_number"] == 2


def test_search_logs_error_on_bad_query(db_with_indexed_source, caplog):
    """Malformed FTS query should log a warning and return []."""
    import logging
    engine, _ = db_with_indexed_source
    with caplog.at_level(logging.WARNING, logger="app.services.search_service"):
        results = search_fulltext(engine, '"unclosed_quote')
    assert results == []
    assert len(caplog.records) >= 1
