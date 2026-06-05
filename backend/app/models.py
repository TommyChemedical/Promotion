from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    authors = Column(String, default="")
    year = Column(Integer, nullable=True)
    doi = Column(String, default="")
    journal = Column(String, default="")
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    texts = relationship("DocumentText", back_populates="source", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="source", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="source", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="source", cascade="all, delete-orphan")
    llm_runs = relationship("LLMRun", back_populates="source", cascade="all, delete-orphan")
    source_tags = relationship("SourceTag", back_populates="source", cascade="all, delete-orphan")
    research_area_links = relationship("SourceResearchArea", back_populates="source", cascade="all, delete-orphan")


class DocumentText(Base):
    __tablename__ = "document_texts"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)

    source = relationship("Source", back_populates="texts")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    model_name = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    research_question = Column(Text, default="")
    methods = Column(Text, default="")
    data_basis = Column(Text, default="")
    key_results = Column(Text, default="[]")
    limitations = Column(Text, default="")
    relevance = Column(Text, default="")
    uncertainty_notes = Column(Text, default="")
    review_status = Column(String, default="unreviewed")
    review_comment = Column(Text, default="")
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, server_default="local_user")
    confidence_user = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="summaries")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)

    source_tags = relationship("SourceTag", back_populates="tag", cascade="all, delete-orphan")


class SourceTag(Base):
    __tablename__ = "source_tags"

    source_id = Column(Integer, ForeignKey("sources.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    source = relationship("Source", back_populates="source_tags")
    tag = relationship("Tag", back_populates="source_tags")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    claim = Column(Text, nullable=False)
    evidence_text = Column(Text, default="")
    evidence_quote = Column(Text, default="")
    page_number = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    page_start = Column(Integer, nullable=True)
    validation_method = Column(String, nullable=False, default="none")
    validation_score = Column(Float, nullable=False, default=0.0)
    validated_at = Column(DateTime, nullable=True)
    relevance = Column(Text, default="")
    confidence = Column(String, default="low")
    validation_status = Column(String, default="no_evidence")
    review_status = Column(String, default="unreviewed")
    review_comment = Column(Text, default="")
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, server_default="local_user")
    confidence_user = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="findings")
    research_area_links = relationship("FindingResearchArea", back_populates="finding", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    text = Column(Text, nullable=False)
    linked_page_number = Column(Integer, nullable=True)
    linked_quote = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="notes")


class LLMRun(Base):
    __tablename__ = "llm_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    task_type = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    output_json = Column(Text, default="")
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="llm_runs")


AREA_TYPES = ("research_question", "chapter", "theme", "argument",
              "method", "theory", "literature_gap", "other")

RELEVANCE_VALUES = ("central", "useful", "marginal", "context_only", "do_not_use")

RELATION_TYPES = ("supports", "contradicts", "differentiates", "defines",
                  "method", "theory", "evidence", "limitation",
                  "research_gap", "background", "other")


class ResearchArea(Base):
    __tablename__ = "research_areas"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    area_type = Column(String, nullable=False, default="other")
    parent_id = Column(Integer, ForeignKey("research_areas.id"), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("ResearchArea", remote_side="ResearchArea.id", foreign_keys="[ResearchArea.parent_id]")
    finding_links = relationship("FindingResearchArea", back_populates="research_area", cascade="all, delete-orphan")
    source_links = relationship("SourceResearchArea", back_populates="research_area", cascade="all, delete-orphan")


class FindingResearchArea(Base):
    __tablename__ = "finding_research_areas"
    __table_args__ = (UniqueConstraint("finding_id", "research_area_id", name="uq_finding_area"),)

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    research_area_id = Column(Integer, ForeignKey("research_areas.id"), nullable=False)
    relevance = Column(String, nullable=False, default="useful")
    relation_type = Column(String, nullable=False, default="other")
    user_comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    finding = relationship("Finding", back_populates="research_area_links")
    research_area = relationship("ResearchArea", back_populates="finding_links")


class SourceResearchArea(Base):
    __tablename__ = "source_research_areas"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    research_area_id = Column(Integer, ForeignKey("research_areas.id"), nullable=False)
    relevance = Column(String, nullable=False, default="useful")
    user_comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("Source", back_populates="research_area_links")
    research_area = relationship("ResearchArea", back_populates="source_links")
