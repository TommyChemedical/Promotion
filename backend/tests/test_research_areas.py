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


def test_research_area_schemas():
    from app.schemas import (
        ResearchAreaCreate, ResearchAreaRead, ResearchAreaUpdate,
        FindingAssignCreate, FindingAssignUpdate, ResearchAreaFindingEntry,
        ResearchAreaOverview,
    )
    create = ResearchAreaCreate(title="Test", area_type="chapter")
    assert create.title == "Test"
    assert create.sort_order == 0

    update = ResearchAreaUpdate(title="Updated")
    assert update.title == "Updated"

    overview = ResearchAreaOverview(
        area_id=1, area_title="T", area_type="chapter",
        count_findings_total=5, count_findings_correct=3,
        count_findings_partially_correct=1, count_findings_unreviewed=1,
        count_evidence_found=4, count_evidence_missing=1,
        count_sources=2, relation_type_counts={}, relevance_counts={},
        top_sources=[], gaps=[],
    )
    assert overview.count_findings_total == 5


# ---------------------------------------------------------------------------
# API (CRUD) tests
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


@pytest.fixture
def area_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c, Session
    app.dependency_overrides.clear()


def test_create_research_area(area_client):
    client, _ = area_client
    r = client.post("/api/research-areas", json={
        "title": "Kapitel 2", "area_type": "chapter", "sort_order": 1
    })
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Kapitel 2"
    assert data["area_type"] == "chapter"
    assert data["id"] is not None


def test_list_research_areas(area_client):
    client, _ = area_client
    client.post("/api/research-areas", json={"title": "A", "area_type": "theme", "sort_order": 0})
    client.post("/api/research-areas", json={"title": "B", "area_type": "argument", "sort_order": 1})
    r = client.get("/api/research-areas")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_research_area(area_client):
    client, _ = area_client
    created = client.post("/api/research-areas", json={"title": "T", "area_type": "other", "sort_order": 0}).json()
    r = client.get(f"/api/research-areas/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "T"


def test_get_research_area_not_found(area_client):
    client, _ = area_client
    r = client.get("/api/research-areas/99999")
    assert r.status_code == 404


def test_update_research_area(area_client):
    client, _ = area_client
    created = client.post("/api/research-areas", json={"title": "Old", "area_type": "other", "sort_order": 0}).json()
    r = client.patch(f"/api/research-areas/{created['id']}", json={"title": "New"})
    assert r.status_code == 200
    assert r.json()["title"] == "New"
    assert r.json()["area_type"] == "other"  # unchanged


def test_delete_research_area_no_findings(area_client):
    client, _ = area_client
    created = client.post("/api/research-areas", json={"title": "Del", "area_type": "other", "sort_order": 0}).json()
    r = client.delete(f"/api/research-areas/{created['id']}")
    assert r.status_code == 200
    assert client.get(f"/api/research-areas/{created['id']}").status_code == 404


def test_delete_research_area_cascades_assignments(area_client):
    """Delete should succeed even if findings are assigned — assignments are cascade-deleted."""
    client, Session = area_client
    with Session() as session:
        src = Source(title="S", filename="s.pdf", file_path="/s.pdf")
        session.add(src)
        session.flush()
        f = Finding(source_id=src.id, claim="C", evidence_text="", confidence="low")
        session.add(f)
        session.commit()
        finding_id = f.id

    area = client.post("/api/research-areas", json={"title": "A", "area_type": "other", "sort_order": 0}).json()
    client.post(f"/api/research-areas/{area['id']}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.delete(f"/api/research-areas/{area['id']}")
    assert r.status_code == 200
    assert client.get(f"/api/research-areas/{area['id']}").status_code == 404


def test_research_area_hierarchy(area_client):
    client, _ = area_client
    parent = client.post("/api/research-areas", json={"title": "Parent", "area_type": "chapter", "sort_order": 0}).json()
    child = client.post("/api/research-areas", json={
        "title": "Child", "area_type": "theme", "sort_order": 0, "parent_id": parent["id"]
    }).json()
    assert child["parent_id"] == parent["id"]
