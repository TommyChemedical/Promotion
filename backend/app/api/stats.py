from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import LLMRun

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/tokens")
def get_token_stats(
    since: Optional[str] = Query(None, description="ISO timestamp; only count runs after this time"),
    db: Session = Depends(get_db),
):
    q = db.query(
        func.coalesce(func.sum(LLMRun.input_tokens), 0),
        func.coalesce(func.sum(LLMRun.output_tokens), 0),
        func.count(LLMRun.id),
    )
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            q = q.filter(LLMRun.created_at >= since_dt)
        except ValueError:
            pass
    input_total, output_total, run_count = q.one()
    return {
        "input_tokens": int(input_total),
        "output_tokens": int(output_total),
        "total_runs": int(run_count),
    }
