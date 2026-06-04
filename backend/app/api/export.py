import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.export_service import export_to_csv, export_to_markdown

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
def export_csv(db: Session = Depends(get_db)):
    content = export_to_csv(db)
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=literaturki_export.csv"},
    )


@router.get("/markdown")
def export_markdown(db: Session = Depends(get_db)):
    content = export_to_markdown(db)
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=literaturki_export.md"},
    )
