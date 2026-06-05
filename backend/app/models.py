from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
    reviewed_by = Column(String, default="local_user")
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
    relevance = Column(Text, default="")
    confidence = Column(String, default="low")
    validation_status = Column(String, default="no_evidence")
    review_status = Column(String, default="unreviewed")
    review_comment = Column(Text, default="")
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, default="local_user")
    confidence_user = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="findings")


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
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="llm_runs")
