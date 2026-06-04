from fastapi import APIRouter, Query
from app.database import engine
from app.services.search_service import search_fulltext

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(q: str = Query(..., min_length=2)):
    return search_fulltext(engine, q)
