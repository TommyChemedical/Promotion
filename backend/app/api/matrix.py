import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import MatrixFilters, MatrixResponse
from app.services.matrix_service import (
    build_matrix_rows, apply_filters, build_response,
    export_matrix_csv, export_matrix_markdown,
)

router = APIRouter(prefix="/api/matrix", tags=["matrix"])


def _parse_filters(
    q: Optional[str] = Query(None),
    tag: list[str] = Query(default=[]),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None),
    validation_status: Optional[str] = Query(None),
    has_evidence: Optional[bool] = Query(None),
    only_reviewed: bool = Query(False),
    only_unreviewed: bool = Query(False),
    source_id: Optional[int] = Query(None),
    research_area_id: Optional[int] = Query(None),
    relation_type: Optional[str] = Query(None),
    relevance: Optional[str] = Query(None),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> MatrixFilters:
    return MatrixFilters(
        q=q, tag=tag, year_from=year_from, year_to=year_to,
        review_status=review_status, validation_status=validation_status,
        has_evidence=has_evidence, only_reviewed=only_reviewed,
        only_unreviewed=only_unreviewed, source_id=source_id,
        research_area_id=research_area_id, relation_type=relation_type,
        relevance=relevance,
        sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset,
    )


@router.get("", response_model=MatrixResponse)
def get_matrix(
    filters: MatrixFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
) -> MatrixResponse:
    all_rows = build_matrix_rows(db)
    filtered = apply_filters(all_rows, filters)
    return build_response(filtered, filters, all_rows)


@router.get("/export.csv")
def export_csv(
    filters: MatrixFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    all_rows = build_matrix_rows(db)
    filtered = apply_filters(all_rows, filters)
    content = export_matrix_csv(filtered)
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=matrix_export.csv"},
    )


@router.get("/export.md")
def export_md(
    filters: MatrixFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    all_rows = build_matrix_rows(db)
    filtered = apply_filters(all_rows, filters)
    content = export_matrix_markdown(filtered)
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=matrix_export.md"},
    )
