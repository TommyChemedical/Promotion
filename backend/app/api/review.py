import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Source, Summary, Finding
from app.schemas import (
    ReviewUpdateRequest, ReviewableSummaryResponse, ReviewableFindingResponse,
    SourceReviewResponse, EvidenceValidationResponse, EvidenceValidationResult,
    ValidationStatus, ValidationMethod,
)
from app.services.evidence_service import validate_finding_evidence, get_page_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


def _finding_response(f: Finding, db: Session) -> ReviewableFindingResponse:
    preview = get_page_preview(f.source_id, f.page_start, db, f.evidence_quote or "")
    return ReviewableFindingResponse(
        id=f.id,
        claim=f.claim,
        evidence_text=f.evidence_text or "",
        evidence_quote=f.evidence_quote or "",
        page_start=f.page_start,
        page_end=f.page_end,
        confidence=f.confidence or "low",
        validation_status=ValidationStatus(f.validation_status or "no_evidence"),
        validation_method=ValidationMethod(f.validation_method or "none"),
        validation_score=f.validation_score or 0.0,
        validated_at=f.validated_at,
        review_status=f.review_status or "unreviewed",
        review_comment=f.review_comment or "",
        reviewed_at=f.reviewed_at,
        reviewed_by=f.reviewed_by,
        confidence_user=f.confidence_user,
        page_preview=preview,
        created_at=f.created_at,
    )


@router.get("/sources/{source_id}", response_model=SourceReviewResponse)
def get_source_review(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")

    summary = (
        db.query(Summary)
        .filter_by(source_id=source_id)
        .order_by(Summary.created_at.desc())
        .first()
    )
    findings = (
        db.query(Finding)
        .filter_by(source_id=source_id)
        .order_by(Finding.id)
        .all()
    )

    summary_resp = None
    if summary:
        summary_resp = ReviewableSummaryResponse.model_validate(summary)

    return SourceReviewResponse(
        source_id=source_id,
        summary=summary_resp,
        findings=[_finding_response(f, db) for f in findings],
    )


@router.patch("/summary/{summary_id}", response_model=ReviewableSummaryResponse)
def patch_summary_review(summary_id: int, body: ReviewUpdateRequest, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(404, "Zusammenfassung nicht gefunden")

    summary.review_status = body.review_status.value
    summary.review_comment = body.review_comment
    summary.confidence_user = body.confidence_user
    summary.reviewed_at = datetime.utcnow()
    summary.reviewed_by = "local_user"
    db.commit()
    db.refresh(summary)
    return ReviewableSummaryResponse.model_validate(summary)


@router.patch("/finding/{finding_id}", response_model=ReviewableFindingResponse)
def patch_finding_review(finding_id: int, body: ReviewUpdateRequest, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(404, "Finding nicht gefunden")

    finding.review_status = body.review_status.value
    finding.review_comment = body.review_comment
    finding.confidence_user = body.confidence_user
    finding.reviewed_at = datetime.utcnow()
    finding.reviewed_by = "local_user"
    db.commit()
    db.refresh(finding)
    return _finding_response(finding, db)


@router.post("/source/{source_id}/validate-evidence", response_model=EvidenceValidationResponse)
def validate_all_evidence(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")

    findings = db.query(Finding).filter_by(source_id=source_id).all()
    results = []
    for f in findings:
        result = validate_finding_evidence(f, db)
        f.validation_status = result.status
        f.validation_method = result.method
        f.validation_score = result.score
        f.validated_at = datetime.utcnow()
        results.append(EvidenceValidationResult(
            finding_id=f.id,
            validation_status=ValidationStatus(result.status),
        ))

    db.commit()
    logger.info("Source %d: validated evidence for %d finding(s)", source_id, len(findings))

    return EvidenceValidationResponse(
        source_id=source_id,
        validated=len(findings),
        results=results,
    )
