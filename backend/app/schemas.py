from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


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
    relevance: str = ""
    confidence: str = "low"


class FindingRead(BaseModel):
    id: int
    claim: str
    evidence_text: str
    evidence_quote: str = ""
    page_number: Optional[int] = None
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
    invalid_page = "invalid_page"


class ValidationMethod(str, Enum):
    none = "none"
    exact = "exact"
    fragment = "fragment"
    fuzzy = "fuzzy"


class ReviewUpdateRequest(BaseModel):
    review_status: ReviewStatus
    review_comment: str = ""
    confidence_user: Optional[int] = Field(None, ge=1, le=5)


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
    confidence_user: Optional[int] = Field(None, ge=1, le=5)
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewableFindingResponse(BaseModel):
    id: int
    claim: str
    evidence_text: str
    evidence_quote: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    confidence: str
    validation_status: ValidationStatus
    validation_method: ValidationMethod = ValidationMethod.none
    validation_score: float = 0.0
    validated_at: Optional[datetime] = None
    review_status: ReviewStatus
    review_comment: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    confidence_user: Optional[int] = Field(None, ge=1, le=5)
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


# --- Matrix types ---

class MatrixRow(BaseModel):
    source_id: int
    source_title: str
    authors: str
    year: Optional[int]
    doi: str
    journal: str
    source_review_status: str
    finding_id: Optional[int]
    finding_statement: Optional[str]
    finding_page_start: Optional[int]
    finding_page_end: Optional[int]
    evidence_quote: Optional[str]
    validation_status: Optional[str]
    validation_method: Optional[str]
    validation_score: Optional[float]
    finding_review_status: Optional[str]
    finding_review_comment: Optional[str]
    confidence_user: Optional[int]
    summary_short: Optional[str]
    summary_review_status: Optional[str]
    tags: list[str]
    notes_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class MatrixFilters(BaseModel):
    q: Optional[str] = None
    tag: list[str] = Field(default_factory=list)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    review_status: Optional[str] = None
    validation_status: Optional[str] = None
    has_evidence: Optional[bool] = None
    only_reviewed: bool = False
    only_unreviewed: bool = False
    source_id: Optional[int] = None
    sort_by: str = "updated_at"
    sort_order: str = "desc"
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class MatrixResponse(BaseModel):
    items: list[MatrixRow]
    total: int
    limit: int
    offset: int
    filters_applied: dict[str, Any]


# --- Research Map types ---

class ResearchAreaCreate(BaseModel):
    title: str
    description: str = ""
    area_type: str = "other"
    parent_id: Optional[int] = None
    sort_order: int = 0


class ResearchAreaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    area_type: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class ResearchAreaRead(BaseModel):
    id: int
    title: str
    description: str
    area_type: str
    parent_id: Optional[int]
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FindingAssignCreate(BaseModel):
    finding_id: int
    relevance: str = "useful"
    relation_type: str = "other"
    user_comment: str = ""


class FindingAssignUpdate(BaseModel):
    relevance: Optional[str] = None
    relation_type: Optional[str] = None
    user_comment: Optional[str] = None


class ResearchAreaFindingEntry(BaseModel):
    """One finding assigned to a research area — enriched with source info."""
    link_id: int
    finding_id: int
    relevance: str
    relation_type: str
    user_comment: str
    # Finding fields
    claim: str
    evidence_quote: str
    evidence_text: str
    page_start: Optional[int]
    page_end: Optional[int]
    confidence: str
    validation_status: str
    validation_method: str
    finding_review_status: str
    finding_review_comment: str
    # Source fields
    source_id: int
    source_title: str
    authors: str
    year: Optional[int]
    doi: str
    tags: list[str]
    summary_short: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TopSourceEntry(BaseModel):
    source_id: int
    source_title: str
    authors: str
    year: Optional[int]
    finding_count: int


class ResearchAreaOverview(BaseModel):
    area_id: int
    area_title: str
    area_type: str
    count_findings_total: int
    count_findings_correct: int
    count_findings_partially_correct: int
    count_findings_unreviewed: int
    count_evidence_found: int
    count_evidence_missing: int
    count_sources: int
    relation_type_counts: dict[str, int]
    relevance_counts: dict[str, int]
    top_sources: list[TopSourceEntry]
    gaps: list[str]


class ResearchAreaRef(BaseModel):
    """Compact reference used inside MatrixRow."""
    research_area_id: int
    title: str
    area_type: str
    relevance: str
    relation_type: str
