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


@pytest.fixture
def area_with_finding(area_client):
    client, Session = area_client
    with Session() as session:
        src = Source(title="Src", filename="s.pdf", file_path="/s.pdf",
                     authors="A. Author", year=2023, doi="", journal="")
        session.add(src)
        session.flush()
        f = Finding(source_id=src.id, claim="Finding claim",
                    evidence_text="some text", evidence_quote="verbatim quote",
                    page_start=3, page_end=3, confidence="high",
                    validation_status="evidence_found", validation_method="exact",
                    validation_score=1.0, review_status="correct",
                    review_comment="Good")
        session.add(f)
        session.commit()
        finding_id = f.id
        source_id = src.id

    area = client.post("/api/research-areas", json={"title": "Area A", "area_type": "argument", "sort_order": 0}).json()
    return client, Session, area["id"], finding_id, source_id


def test_assign_finding(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    r = client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports",
        "user_comment": "Strong support"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["finding_id"] == finding_id
    assert data["relevance"] == "central"
    assert data["relation_type"] == "supports"
    assert data["claim"] == "Finding claim"
    assert data["source_title"] == "Src"
    assert data["year"] == 2023


def test_assign_finding_duplicate_raises_409(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "useful", "relation_type": "other"
    })
    assert r.status_code == 409


def test_assign_finding_invalid_finding_id(area_with_finding):
    client, _, area_id, _, _ = area_with_finding
    r = client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": 99999, "relevance": "central", "relation_type": "supports"
    })
    assert r.status_code == 404


def test_assign_finding_invalid_area_id(area_with_finding):
    client, _, _, finding_id, _ = area_with_finding
    r = client.post("/api/research-areas/99999/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    assert r.status_code == 404


def test_update_finding_assignment(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.patch(f"/api/research-areas/{area_id}/findings/{finding_id}", json={
        "relevance": "marginal", "user_comment": "Reconsidered"
    })
    assert r.status_code == 200
    assert r.json()["relevance"] == "marginal"
    assert r.json()["relation_type"] == "supports"  # unchanged


def test_delete_finding_assignment(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.delete(f"/api/research-areas/{area_id}/findings/{finding_id}")
    assert r.status_code == 200
    r2 = client.get(f"/api/research-areas/{area_id}/findings")
    assert r2.json() == []


def test_list_findings_for_area(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.get(f"/api/research-areas/{area_id}/findings")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["claim"] == "Finding claim"
    assert items[0]["evidence_quote"] == "verbatim quote"
    assert items[0]["validation_status"] == "evidence_found"


def test_list_findings_filter_review_status(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.get(f"/api/research-areas/{area_id}/findings?review_status=correct")
    assert len(r.json()) == 1

    r2 = client.get(f"/api/research-areas/{area_id}/findings?review_status=incorrect")
    assert len(r2.json()) == 0


def test_overview_counts(area_with_finding):
    client, Session, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.get(f"/api/research-areas/{area_id}/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["count_findings_total"] == 1
    assert data["count_findings_correct"] == 1
    assert data["count_evidence_found"] == 1
    assert data["count_sources"] == 1
    assert data["relevance_counts"]["central"] == 1
    assert data["relation_type_counts"]["supports"] == 1


def test_overview_gaps_unreviewed(area_with_finding):
    """Gap 'Viele unreviewed Findings' appears when majority are unreviewed."""
    client, Session, area_id, _, _ = area_with_finding
    with Session() as session:
        src = Source(title="S2", filename="s2.pdf", file_path="/s2.pdf")
        session.add(src)
        session.flush()
        f2 = Finding(source_id=src.id, claim="Unreviewed", evidence_text="",
                     confidence="low", review_status="unreviewed",
                     validation_status="no_evidence")
        session.add(f2)
        session.commit()
        f2_id = f2.id

    area2 = client.post("/api/research-areas", json={"title": "B", "area_type": "other", "sort_order": 0}).json()
    client.post(f"/api/research-areas/{area2['id']}/findings", json={
        "finding_id": f2_id, "relevance": "useful", "relation_type": "other"
    })
    r = client.get(f"/api/research-areas/{area2['id']}/overview")
    assert "Viele unreviewed Findings" in r.json()["gaps"]


def test_overview_gaps_no_central(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "marginal", "relation_type": "other"
    })
    r = client.get(f"/api/research-areas/{area_id}/overview")
    assert "Keine zentralen Findings" in r.json()["gaps"]


def test_overview_gaps_single_source(area_with_finding):
    client, _, area_id, finding_id, _ = area_with_finding
    client.post(f"/api/research-areas/{area_id}/findings", json={
        "finding_id": finding_id, "relevance": "central", "relation_type": "supports"
    })
    r = client.get(f"/api/research-areas/{area_id}/overview")
    assert "Nur eine Quelle in diesem Bereich" in r.json()["gaps"]


def test_overview_empty_area(area_with_finding):
    client, _, area_id, _, _ = area_with_finding
    r = client.get(f"/api/research-areas/{area_id}/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["count_findings_total"] == 0
    assert data["gaps"] == []
