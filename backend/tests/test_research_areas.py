import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, ResearchArea, FindingResearchArea, SourceResearchArea, Source, Finding


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session


def test_research_area_model_exists(db):
    area = ResearchArea(title="Kapitel 2", area_type="chapter", sort_order=1)
    db.add(area)
    db.commit()
    assert area.id is not None
    assert area.title == "Kapitel 2"
    assert area.area_type == "chapter"
    assert area.parent_id is None
    assert area.created_at is not None


def test_research_area_hierarchy(db):
    parent = ResearchArea(title="Parent", area_type="chapter", sort_order=0)
    db.add(parent)
    db.flush()
    child = ResearchArea(title="Child", area_type="theme", sort_order=0, parent_id=parent.id)
    db.add(child)
    db.commit()
    assert child.parent_id == parent.id


def test_finding_research_area_model(db):
    src = Source(title="T", filename="f.pdf", file_path="/f.pdf")
    db.add(src)
    db.flush()
    finding = Finding(source_id=src.id, claim="Claim", evidence_text="", confidence="high")
    db.add(finding)
    db.flush()
    area = ResearchArea(title="A", area_type="argument", sort_order=0)
    db.add(area)
    db.flush()
    link = FindingResearchArea(
        finding_id=finding.id, research_area_id=area.id,
        relevance="central", relation_type="supports",
    )
    db.add(link)
    db.commit()
    assert link.id is not None


def test_source_research_area_model(db):
    src = Source(title="T", filename="f.pdf", file_path="/f.pdf")
    db.add(src)
    db.flush()
    area = ResearchArea(title="A", area_type="theme", sort_order=0)
    db.add(area)
    db.flush()
    link = SourceResearchArea(source_id=src.id, research_area_id=area.id, relevance="useful")
    db.add(link)
    db.commit()
    assert link.id is not None


def test_research_area_unique_constraint(db):
    """No unique constraint — multiple areas can share a title."""
    a1 = ResearchArea(title="Same", area_type="other", sort_order=0)
    a2 = ResearchArea(title="Same", area_type="other", sort_order=1)
    db.add_all([a1, a2])
    db.commit()
    assert a1.id != a2.id


def test_finding_research_area_unique_pair(db):
    """Same finding+area pair should raise IntegrityError on second insert."""
    from sqlalchemy.exc import IntegrityError
    src = Source(title="T", filename="f.pdf", file_path="/f.pdf")
    db.add(src)
    db.flush()
    f = Finding(source_id=src.id, claim="C", evidence_text="", confidence="low")
    db.add(f)
    db.flush()
    area = ResearchArea(title="A", area_type="other", sort_order=0)
    db.add(area)
    db.flush()
    db.add(FindingResearchArea(finding_id=f.id, research_area_id=area.id, relevance="central", relation_type="supports"))
    db.commit()
    db.add(FindingResearchArea(finding_id=f.id, research_area_id=area.id, relevance="useful", relation_type="other"))
    with pytest.raises(IntegrityError):
        db.commit()
