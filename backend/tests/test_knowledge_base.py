import uuid

from tests.test_new_features import _create_client
from tests.test_projects import _create_project

KB_URL = "/knowledge-base"


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _create_client_with_industry(admin_client, industry, **overrides):
    payload = {"industry": industry}
    payload.update(overrides)
    return _create_client(admin_client, email=_unique_email("kb-client"), **payload)


def test_project_without_close_out_notes_excluded(admin_client):
    client = _create_client_with_industry(admin_client, "Manufacturing")
    _create_project(admin_client, client["id"], name="No Retro Yet")

    resp = admin_client.get(f"{KB_URL}/")
    assert resp.status_code == 200, resp.text
    names = {r["project_name"] for r in resp.json()["results"]}
    assert "No Retro Yet" not in names


def test_project_with_close_out_notes_included(admin_client):
    client = _create_client_with_industry(admin_client, "Manufacturing")
    project = _create_project(
        admin_client,
        client["id"],
        name="Widget Co FY26 Audit",
        close_out_notes="Client had a going concern issue flagged mid-engagement; resolved after management plan review.",
    )

    resp = admin_client.get(f"{KB_URL}/")
    assert resp.status_code == 200, resp.text
    entry = next(r for r in resp.json()["results"] if r["project_id"] == project["id"])
    assert entry["client_industry"] == "Manufacturing"
    assert "going concern" in entry["close_out_notes"].lower()


def test_search_matches_known_phrase(admin_client):
    client = _create_client_with_industry(admin_client, "Retail")
    project = _create_project(
        admin_client,
        client["id"],
        name="Retail Co Audit",
        close_out_notes="We identified a material weakness in revenue recognition controls.",
    )
    other_client = _create_client_with_industry(admin_client, "Retail")
    _create_project(
        admin_client,
        other_client["id"],
        name="Unrelated Engagement",
        close_out_notes="Straightforward engagement, no issues of note.",
    )

    resp = admin_client.get(f"{KB_URL}/", params={"q": "material weakness"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    project_ids = {r["project_id"] for r in body["results"]}
    assert project["id"] in project_ids
    matched_entry = next(r for r in body["results"] if r["project_id"] == project["id"])
    assert "material weakness" in matched_entry["matched_terms"]
    assert matched_entry["snippet"] is not None


def test_search_no_match_returns_empty(admin_client):
    client = _create_client_with_industry(admin_client, "Healthcare")
    _create_project(
        admin_client,
        client["id"],
        name="Healthcare Co Audit",
        close_out_notes="Clean engagement, nothing noteworthy.",
    )

    resp = admin_client.get(f"{KB_URL}/", params={"q": "fraud risk"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"] == []


def test_filter_by_engagement_type(admin_client):
    client = _create_client_with_industry(admin_client, "Tech")
    audit_project = _create_project(
        admin_client,
        client["id"],
        name="Tech Co Audit",
        type="audit",
        close_out_notes="Audit retrospective notes.",
    )
    tax_project = _create_project(
        admin_client,
        client["id"],
        name="Tech Co Tax",
        type="tax",
        close_out_notes="Tax retrospective notes.",
    )

    resp = admin_client.get(f"{KB_URL}/", params={"engagement_type": "tax"})
    assert resp.status_code == 200, resp.text
    project_ids = {r["project_id"] for r in resp.json()["results"]}
    assert tax_project["id"] in project_ids
    assert audit_project["id"] not in project_ids


def test_filter_by_industry(admin_client):
    manufacturing_client = _create_client_with_industry(admin_client, "Manufacturing-Unique")
    tech_client = _create_client_with_industry(admin_client, "Tech-Unique")

    mfg_project = _create_project(
        admin_client,
        manufacturing_client["id"],
        name="Mfg Engagement",
        close_out_notes="Manufacturing retrospective.",
    )
    _create_project(
        admin_client,
        tech_client["id"],
        name="Tech Engagement",
        close_out_notes="Tech retrospective.",
    )

    resp = admin_client.get(f"{KB_URL}/", params={"industry": "Manufacturing-Unique"})
    assert resp.status_code == 200, resp.text
    project_ids = {r["project_id"] for r in resp.json()["results"]}
    assert mfg_project["id"] in project_ids
    assert len(resp.json()["results"]) == 1


def test_filter_by_risk_level(admin_client):
    client = _create_client_with_industry(admin_client, "Finance")
    high_risk = _create_project(
        admin_client,
        client["id"],
        name="High Risk Engagement",
        risk_level="high",
        close_out_notes="High risk retrospective.",
    )
    _create_project(
        admin_client,
        client["id"],
        name="Low Risk Engagement",
        risk_level="low",
        close_out_notes="Low risk retrospective.",
    )

    resp = admin_client.get(f"{KB_URL}/", params={"risk_level": "high"})
    assert resp.status_code == 200, resp.text
    project_ids = {r["project_id"] for r in resp.json()["results"]}
    assert high_risk["id"] in project_ids
    assert len(resp.json()["results"]) == 1


def test_filter_by_client_id(admin_client):
    client_a = _create_client_with_industry(admin_client, "Energy")
    client_b = _create_client_with_industry(admin_client, "Energy")
    project_a = _create_project(admin_client, client_a["id"], name="A Engagement", close_out_notes="Notes A")
    _create_project(admin_client, client_b["id"], name="B Engagement", close_out_notes="Notes B")

    resp = admin_client.get(f"{KB_URL}/", params={"client_id": client_a["id"]})
    assert resp.status_code == 200, resp.text
    project_ids = {r["project_id"] for r in resp.json()["results"]}
    assert project_ids == {project_a["id"]}


def test_facets_reflect_only_entries_with_notes(admin_client):
    client = _create_client_with_industry(admin_client, "FacetIndustryUnique")
    _create_project(
        admin_client,
        client["id"],
        name="Facet Engagement",
        type="advisory",
        risk_level="high",
        compliance_flag="SOX",
        close_out_notes="Facet retrospective notes.",
    )
    _create_project(admin_client, client["id"], name="No Notes Engagement", type="tax")

    resp = admin_client.get(f"{KB_URL}/facets")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "advisory" in body["engagement_types"]
    assert "FacetIndustryUnique" in body["industries"]
    assert "SOX" in body["compliance_flags"]
    assert "high" in body["risk_levels"]
    assert body["total_entries"] >= 1


def test_knowledge_base_requires_auth(client):
    resp = client.get(f"{KB_URL}/")
    assert resp.status_code == 401
