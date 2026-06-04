from sqlalchemy import text
from sqlalchemy.engine import Engine


def index_document_text(engine: Engine, rowid: int, content: str, source_id: int, page_number: int) -> None:
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO document_text_fts(rowid, text, source_id, page_number) VALUES (:r, :t, :s, :p)"),
            {"r": rowid, "t": content, "s": source_id, "p": page_number},
        )
        conn.commit()


def search_fulltext(engine: Engine, query: str, limit: int = 50) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT source_id, page_number,
                       snippet(document_text_fts, 0, '<b>', '</b>', '...', 20) AS snippet
                FROM document_text_fts
                WHERE text MATCH :q
                LIMIT :limit
            """),
            {"q": query, "limit": limit},
        ).fetchall()
    return [{"source_id": r.source_id, "page_number": r.page_number, "snippet": r.snippet} for r in rows]
