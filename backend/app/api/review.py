import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Source, Summary, Finding
from app.schemas import (
    ReviewUpdateRequest, ReviewableSummaryResponse, ReviewableFindingResponse,
    SourceReviewResponse, EvidenceValidationResponse, EvidenceValidationResult,
    ValidationStatus,
)
from app.services.evidence_service import validate_finding_evidence, get_page_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


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

    finding_resps = []
    for f in findings:
        preview = get_page_preview(source_id, f.page_number, db, f.evidence_quote or "")
        resp = ReviewableFindingResponse(
            id=f.id,
            claim=f.claim,
            evidence_text=f.evidence_text or "",
            evidence_quote=f.evidence_quote or "",
            page_number=f.page_number,
            confidence=f.confidence or "low",
            validation_status=ValidationStatus(f.validation_status or "no_evidence"),
            review_status=f.review_status or "unreviewed",
            review_comment=f.review_comment or "",
            reviewed_at=f.reviewed_at,
            reviewed_by=f.reviewed_by,
            confidence_user=f.confidence_user,
            page_preview=preview,
            created_at=f.created_at,
        )
        finding_resps.append(resp)

    return SourceReviewResponse(
        source_id=source_id,
        summary=summary_resp,
        findings=finding_resps,
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

    preview = get_page_preview(finding.source_id, finding.page_number, db, finding.evidence_quote or "")
    return ReviewableFindingResponse(
        id=finding.id,
        claim=finding.claim,
        evidence_text=finding.evidence_text or "",
        evidence_quote=finding.evidence_quote or "",
        page_number=finding.page_number,
        confidence=finding.confidence or "low",
        validation_status=ValidationStatus(finding.validation_status or "no_evidence"),
        review_status=finding.review_status or "unreviewed",
        review_comment=finding.review_comment or "",
        reviewed_at=finding.reviewed_at,
        reviewed_by=finding.reviewed_by,
        confidence_user=finding.confidence_user,
        page_preview=preview,
        created_at=finding.created_at,
    )


@router.post("/source/{source_id}/validate-evidence", response_model=EvidenceValidationResponse)
def validate_all_evidence(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden")

    findings = db.query(Finding).filter_by(source_id=source_id).all()
    results = []
    for f in findings:
        status = validate_finding_evidence(f, db)
        f.validation_status = status
        results.append(EvidenceValidationResult(
            finding_id=f.id,
            validation_status=ValidationStatus(status),
        ))

    db.commit()
    logger.info("Source %d: validated evidence for %d finding(s)", source_id, len(findings))

    return EvidenceValidationResponse(
        source_id=source_id,
        validated=len(findings),
        results=results,
    )
