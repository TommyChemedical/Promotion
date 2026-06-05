from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _create_fts_table()
    _run_migrations()


def _create_fts_table():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS document_text_fts
            USING fts5(text, source_id UNINDEXED, page_number UNINDEXED)
        """))
        conn.commit()


def _run_migrations():
    """Add new columns to existing tables. Safe to run on fresh and existing DBs."""
    new_columns = [
        ("findings", "evidence_quote TEXT NOT NULL DEFAULT ''"),
        ("findings", "page_end INTEGER"),
        ("findings", "validation_status TEXT NOT NULL DEFAULT 'no_evidence'"),
        ("findings", "review_status TEXT NOT NULL DEFAULT 'unreviewed'"),
        ("findings", "review_comment TEXT NOT NULL DEFAULT ''"),
        ("findings", "reviewed_at DATETIME"),
        ("findings", "reviewed_by TEXT"),
        ("findings", "confidence_user INTEGER"),
        ("summaries", "review_status TEXT NOT NULL DEFAULT 'unreviewed'"),
        ("summaries", "review_comment TEXT NOT NULL DEFAULT ''"),
        ("summaries", "reviewed_at DATETIME"),
        ("summaries", "reviewed_by TEXT"),
        ("summaries", "confidence_user INTEGER"),
        ("findings", "page_start INTEGER"),
        ("findings", "validation_method TEXT NOT NULL DEFAULT 'none'"),
        ("findings", "validation_score REAL NOT NULL DEFAULT 0.0"),
        ("findings", "validated_at DATETIME"),
        ("llm_runs", "input_tokens INTEGER NOT NULL DEFAULT 0"),
        ("llm_runs", "output_tokens INTEGER NOT NULL DEFAULT 0"),
    ]
    with engine.connect() as conn:
        for table, col_def in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
            except OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
        conn.execute(text(
            "UPDATE findings SET page_start = page_number WHERE page_start IS NULL"
        ))
        conn.commit()
