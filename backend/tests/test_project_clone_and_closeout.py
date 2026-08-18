from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def test_clone_project_basic_fields(admin_client):
    client = _create_client(admin_client, email="clone-basic@example.com")
    source = _create_project(
        admin_client,
        client["id"],
        name="FY26 Annual Audit",
        risk_level="medium",
        budget="20000.00",
    )

    resp = admin_client.post(f"/projects/{source['id']}/clone", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    cloned = body["project"]

    assert cloned["id"] != source["id"]
    assert cloned["name"] == "FY26 Annual Audit (Renewal)"
    assert cloned["client_id"] == source["client_id"]
    assert cloned["status"] == "planning"
    assert cloned["risk_level"] == "medium"
    assert float(cloned["budget"]) == 20000.00
    assert cloned["cloned_from_project_id"] == source["id"]


def test_clone_project_custom_name_and_dates(admin_client):
    client = _create_client(admin_client, email="clone-custom@example.com")
    source = _create_project(
        admin_client, client["id"], name="FY26 Audit", start_date="2026-01-01T00:00:00", end_date="2026-03-01T00:00:00"
    )

    resp = admin_client.post(
        f"/projects/{source['id']}/clone",
        json={"name": "FY27 Audit", "start_date": "2027-01-01T00:00:00", "end_date": "2027-03-01T00:00:00"},
    )
    body = resp.json()["project"]
    assert body["name"] == "FY27 Audit"
    assert body["start_date"].startswith("2027-01-01")


def test_clone_project_copies_milestones_with_shifted_dates(admin_client):
    client = _create_client(admin_client, email="clone-milestones@example.com")
    source = _create_project(admin_client, client["id"], start_date="2026-01-01T00:00:00")
    admin_client.post(
        "/milestones/",
        json={"project_id": source["id"], "name": "Fieldwork complete", "due_date": "2026-02-01T00:00:00"},
    )

    resp = admin_client.post(
        f"/projects/{source['id']}/clone",
        json={"start_date": "2027-01-01T00:00:00", "include_milestones": True},
    )
    body = resp.json()
    assert body["milestones_cloned"] == 1

    milestones = admin_client.get(f"/milestones/?project_id={body['project']['id']}").json()
    assert len(milestones) == 1
    assert milestones[0]["due_date"].startswith("2027-02-01")
    assert milestones[0]["status"] == "pending"


def test_clone_project_copies_team_assignments(admin_client):
    client = _create_client(admin_client, email="clone-team@example.com")
    source = _create_project(admin_client, client["id"])

    me = admin_client.get("/auth/me").json()
    resp = admin_client.post(
        f"/projects/{source['id']}/assignments", json={"user_id": me["id"], "role": "Lead"}
    )
    assert resp.status_code == 200, resp.text

    resp = admin_client.post(f"/projects/{source['id']}/clone", json={"include_team": True})
    body = resp.json()
    assert body["assignments_cloned"] == 1

    assignments = admin_client.get(f"/projects/{body['project']['id']}/assignments").json()
    assert len(assignments) == 1
    assert assignments[0]["role"] == "Lead"


def test_clone_project_skips_milestones_when_not_requested(admin_client):
    client = _create_client(admin_client, email="clone-skip@example.com")
    source = _create_project(admin_client, client["id"])
    admin_client.post("/milestones/", json={"project_id": source["id"], "name": "Some milestone"})

    resp = admin_client.post(f"/projects/{source['id']}/clone", json={"include_milestones": False})
    body = resp.json()
    assert body["milestones_cloned"] == 0


def test_clone_project_rejects_unknown_project(admin_client):
    resp = admin_client.post("/projects/999999/clone", json={})
    assert resp.status_code == 404


def test_clone_project_rejects_backwards_dates(admin_client):
    client = _create_client(admin_client, email="clone-baddates@example.com")
    source = _create_project(admin_client, client["id"])

    resp = admin_client.post(
        f"/projects/{source['id']}/clone",
        json={"start_date": "2027-06-01T00:00:00", "end_date": "2027-01-01T00:00:00"},
    )
    assert resp.status_code == 400


# --- Close-out notes --------------------------------------------------


def test_project_close_out_notes_can_be_set(admin_client):
    client = _create_client(admin_client, email="closeout@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.put(
        f"/projects/{project['id']}",
        json={"status": "completed", "close_out_notes": "Went smoothly; client wants earlier kickoff next year."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert "earlier kickoff" in body["close_out_notes"]


def test_project_close_out_notes_optional(admin_client):
    client = _create_client(admin_client, email="closeout-optional@example.com")
    project = _create_project(admin_client, client["id"])
    assert project["close_out_notes"] is None
