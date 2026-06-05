from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class SourceBase(BaseModel):
    title: str
    authors: str = ""
    year: Optional[int] = None
    doi: str = ""
    journal: str = ""


class SourceRead(SourceBase):
    id: int
    filename: str
    created_at: datetime
    tags: list[str] = []

    model_config = {"from_attributes": True}


class DocumentTextRead(BaseModel):
    id: int
    page_number: int
    text: str

    model_config = {"from_attributes": True}


class FindingCreate(BaseModel):
    claim: str
    evidence_text: str = ""
    evidence_quote: str = ""
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    relevance: str = ""
    confidence: str = "low"


class FindingRead(BaseModel):
    id: int
    claim: str
    evidence_text: str
    evidence_quote: str = ""
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    relevance: str
    confidence: str
    validation_status: str = "no_evidence"
    review_status: str = "unreviewed"
    review_comment: str = ""
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    confidence_user: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteCreate(BaseModel):
    text: str
    linked_page_number: Optional[int] = None
    linked_quote: str = ""


class NoteRead(NoteCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str


class SummaryRead(BaseModel):
    id: int
    model_name: str
    prompt_version: str
    research_question: str
    methods: str
    data_basis: str
    key_results: str  # JSON string
    limitations: str
    relevance: str
    uncertainty_notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceDetail(SourceRead):
    texts: list[DocumentTextRead] = []
    summaries: list[SummaryRead] = []
    findings: list[FindingRead] = []
    notes: list[NoteRead] = []


class ReviewStatus(str, Enum):
    unreviewed = "unreviewed"
    correct = "correct"
    partially_correct = "partially_correct"
    incorrect = "incorrect"
    unsupported = "unsupported"
    missing_important_context = "missing_important_context"


class ValidationStatus(str, Enum):
    no_evidence = "no_evidence"
    evidence_found = "evidence_found"
    evidence_not_found = "evidence_not_found"


class ReviewUpdateRequest(BaseModel):
    review_status: ReviewStatus
    review_comment: str = ""
    confidence_user: Optional[int] = None


class ReviewableSummaryResponse(BaseModel):
    id: int
    research_question: str
    methods: str
    data_basis: str
    limitations: str
    relevance: str
    uncertainty_notes: str
    review_status: ReviewStatus
    review_comment: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    confidence_user: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewableFindingResponse(BaseModel):
    id: int
    claim: str
    evidence_text: str
    evidence_quote: str
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    confidence: str
    validation_status: ValidationStatus
    review_status: ReviewStatus
    review_comment: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    confidence_user: Optional[int] = None
    page_preview: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceReviewResponse(BaseModel):
    source_id: int
    summary: Optional[ReviewableSummaryResponse] = None
    findings: list[ReviewableFindingResponse] = []


class EvidenceValidationResult(BaseModel):
    finding_id: int
    validation_status: ValidationStatus


class EvidenceValidationResponse(BaseModel):
    source_id: int
    validated: int
    results: list[EvidenceValidationResult]
