import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Source, Finding, Summary, Tag, SourceTag, Note
from app.services.export_service import export_to_csv, export_to_markdown


@pytest.fixture
def db_with_data():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        src = Source(
            title="Climate Change and Biodiversity",
            authors="Schmidt, A.; Müller, B.",
            year=2023,
            doi="10.1234/test",
            journal="Nature",
            filename="climate.pdf",
            file_path="/tmp/climate.pdf",
        )
        db.add(src)
        db.flush()

        finding = Finding(
            source_id=src.id,
            claim="CO2 concentration correlates with species loss",
            evidence_text="CO2 concentration correlates with a 15% reduction in species diversity",
            page_number=3,
            confidence="high",
        )
        db.add(finding)

        key_results = json.dumps([{
            "claim": "Temperature rise of 2°C reduces biodiversity by 15%",
            "evidence_text": "At 2°C above pre-industrial levels, biodiversity falls 15%",
            "page_number": 5,
            "confidence": "high",
        }])
        summary = Summary(
            source_id=src.id,
            model_name="claude-sonnet-4-6",
            prompt_version="summary_v1",
            research_question="How does climate change affect biodiversity?",
            methods="Systematic review of 200 studies",
            data_basis="Literature 2000-2023",
            key_results=key_results,
            limitations="Limited to peer-reviewed sources",
            relevance="Directly relevant to dissertation",
            uncertainty_notes="",
        )
        db.add(summary)

        note = Note(source_id=src.id, text="Very important for chapter 2")
        db.add(note)

        tag = Tag(name="climate")
        db.add(tag)
        db.flush()
        db.add(SourceTag(source_id=src.id, tag_id=tag.id))
        db.commit()
        yield db


def test_export_csv_has_header_row(db_with_data):
    csv = export_to_csv(db_with_data)
    lines = csv.strip().split("\n")
    header = lines[0].lower()
    assert "title" in header
    assert "authors" in header


def test_export_csv_contains_source_data(db_with_data):
    csv = export_to_csv(db_with_data)
    assert "Climate Change and Biodiversity" in csv
    assert "Schmidt" in csv
    assert "2023" in csv
    assert "climate" in csv  # tag


def test_export_markdown_has_title(db_with_data):
    md = export_to_markdown(db_with_data)
    assert "# Climate Change and Biodiversity" in md


def test_export_markdown_has_summary(db_with_data):
    md = export_to_markdown(db_with_data)
    assert "How does climate change affect biodiversity?" in md


def test_export_markdown_has_findings(db_with_data):
    md = export_to_markdown(db_with_data)
    assert "CO2 concentration correlates with species loss" in md


def test_export_markdown_shows_confidence(db_with_data):
    md = export_to_markdown(db_with_data)
    assert "HIGH" in md or "high" in md.lower()


def test_export_empty_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        csv = export_to_csv(db)
        md = export_to_markdown(db)
    assert "title" in csv.lower()  # header still present
    assert isinstance(md, str)


def test_csv_sanitizes_formula_injection():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        src = Source(
            title="=CMD('malicious')",
            authors="+dangerous",
            year=2024,
            filename="evil.pdf",
            file_path="/tmp/evil.pdf",
        )
        db.add(src)
        db.commit()
        csv = export_to_csv(db)
    assert "'=CMD" in csv          # sanitized: prefixed with single quote
    assert "'+dangerous" in csv   # sanitized: prefixed with single quote
    # raw formula triggers must not appear as the first character of a field
    for line in csv.splitlines()[1:]:  # skip header
        for field in line.split(","):
            field = field.strip('"')
            assert not (field and field[0] in "=+-@"), f"Unsanitized field: {field!r}"
