from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ResearchArea
from app.schemas import ResearchAreaCreate, ResearchAreaRead, ResearchAreaUpdate

router = APIRouter(prefix="/api/research-areas", tags=["research-areas"])


def _get_area_or_404(area_id: int, db: Session) -> ResearchArea:
    area = db.get(ResearchArea, area_id)
    if not area:
        raise HTTPException(404, "ResearchArea nicht gefunden")
    return area


@router.get("", response_model=list[ResearchAreaRead])
def list_areas(db: Session = Depends(get_db)):
    return (
        db.query(ResearchArea)
        .order_by(ResearchArea.sort_order, ResearchArea.title)
        .all()
    )


@router.post("", response_model=ResearchAreaRead, status_code=201)
def create_area(body: ResearchAreaCreate, db: Session = Depends(get_db)):
    area = ResearchArea(**body.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.get("/{area_id}", response_model=ResearchAreaRead)
def get_area(area_id: int, db: Session = Depends(get_db)):
    return _get_area_or_404(area_id, db)


@router.patch("/{area_id}", response_model=ResearchAreaRead)
def update_area(area_id: int, body: ResearchAreaUpdate, db: Session = Depends(get_db)):
    area = _get_area_or_404(area_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(area, field, value)
    db.commit()
    db.refresh(area)
    return area


@router.delete("/{area_id}")
def delete_area(area_id: int, db: Session = Depends(get_db)):
    area = _get_area_or_404(area_id, db)
    db.delete(area)  # cascade deletes FindingResearchArea + SourceResearchArea
    db.commit()
    return {"ok": True}
