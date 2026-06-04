from datetime import datetime
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
    page_number: Optional[int] = None
    relevance: str = ""
    confidence: str = "low"


class FindingRead(FindingCreate):
    id: int
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
