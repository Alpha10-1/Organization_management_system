from tests.test_new_features import _create_client
from tests.test_projects import _create_project


# --- Per-engagement audit trail -------------------------------------------


def test_project_history_starts_with_creation_entry(admin_client):
    client = _create_client(admin_client, email="history-client@example.com")
    project = _create_project(admin_client, client["id"], name="History Co Audit")

    history = admin_client.get(f"/projects/{project['id']}/history")
    assert history.status_code == 200, history.text
    entries = history.json()
    assert len(entries) == 1
    assert entries[0]["action"] == "project_created"


def test_status_change_recorded_in_history(admin_client):
    client = _create_client(admin_client, email="status-history@example.com")
    project = _create_project(admin_client, client["id"], name="Status Change Co")

    resp = admin_client.put(f"/projects/{project['id']}", json={"status": "active"})
    assert resp.status_code == 200, resp.text

    entries = admin_client.get(f"/projects/{project['id']}/history").json()
    updated = next(e for e in entries if e["action"] == "project_updated")
    assert "planning" in updated["description"]
    assert "active" in updated["description"]


def test_risk_level_change_recorded_as_distinct_entry(admin_client):
    client = _create_client(admin_client, email="risk-history@example.com")
    project = _create_project(admin_client, client["id"], name="Risk Change Co", risk_level="low")

    resp = admin_client.put(f"/projects/{project['id']}", json={"risk_level": "high"})
    assert resp.status_code == 200, resp.text

    entries = admin_client.get(f"/projects/{project['id']}/history").json()
    risk_entries = [e for e in entries if e["action"] == "project_risk_changed"]
    assert len(risk_entries) == 1
    assert "low" in risk_entries[0]["description"]
    assert "high" in risk_entries[0]["description"]


def test_compliance_flag_change_recorded_as_distinct_entry(admin_client):
    client = _create_client(admin_client, email="compliance-history@example.com")
    project = _create_project(admin_client, client["id"], name="Compliance Change Co")

    resp = admin_client.put(f"/projects/{project['id']}", json={"compliance_flag": "SOX"})
    assert resp.status_code == 200, resp.text

    entries = admin_client.get(f"/projects/{project['id']}/history").json()
    risk_entries = [e for e in entries if e["action"] == "project_risk_changed"]
    assert len(risk_entries) == 1
    assert "SOX" in risk_entries[0]["description"]


def test_unrelated_field_update_does_not_create_risk_changed_entry(admin_client):
    client = _create_client(admin_client, email="unrelated-history@example.com")
    project = _create_project(admin_client, client["id"], name="Unrelated Change Co")

    resp = admin_client.put(f"/projects/{project['id']}", json={"description": "Updated scope notes."})
    assert resp.status_code == 200, resp.text

    entries = admin_client.get(f"/projects/{project['id']}/history").json()
    assert not any(e["action"] == "project_risk_changed" for e in entries)


def test_history_ordered_newest_first(admin_client):
    client = _create_client(admin_client, email="ordered-history@example.com")
    project = _create_project(admin_client, client["id"], name="Ordered Co", risk_level="low")

    admin_client.put(f"/projects/{project['id']}", json={"risk_level": "medium"})
    admin_client.put(f"/projects/{project['id']}", json={"risk_level": "high"})

    entries = admin_client.get(f"/projects/{project['id']}/history").json()
    timestamps = [e["created_at"] for e in entries]
    assert timestamps == sorted(timestamps, reverse=True)


def test_history_404_for_missing_project(admin_client):
    resp = admin_client.get("/projects/999999/history")
    assert resp.status_code == 404


def test_staff_can_view_project_history(staff_client, admin_client):
    client = _create_client(admin_client, email="staff-history@example.com")
    project = _create_project(admin_client, client["id"], name="Staff Visible Co")

    resp = staff_client.get(f"/projects/{project['id']}/history")
    assert resp.status_code == 200, resp.text


# --- Firm-wide compliance dashboard ---------------------------------------


def test_compliance_dashboard_includes_high_risk_open_engagement(admin_client):
    client = _create_client(admin_client, email="dash-high-risk@example.com")
    project = _create_project(
        admin_client, client["id"], name="High Risk Dash Co", status="active", risk_level="high"
    )

    resp = admin_client.get("/reports/dashboard/compliance")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["high_risk_count"] >= 1
    assert any(e["id"] == project["id"] for e in body["engagements"])


def test_compliance_dashboard_excludes_low_risk_unflagged_engagement(admin_client):
    client = _create_client(admin_client, email="dash-low-risk@example.com")
    project = _create_project(
        admin_client, client["id"], name="Low Risk Dash Co", status="active", risk_level="low"
    )

    resp = admin_client.get("/reports/dashboard/compliance")
    body = resp.json()
    assert not any(e["id"] == project["id"] for e in body["engagements"])


def test_compliance_dashboard_includes_flagged_low_risk_engagement(admin_client):
    client = _create_client(admin_client, email="dash-flagged@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        name="Flagged Dash Co",
        status="active",
        risk_level="low",
        compliance_flag="PCAOB",
    )

    resp = admin_client.get("/reports/dashboard/compliance")
    body = resp.json()
    assert any(e["id"] == project["id"] for e in body["engagements"])
    assert body["compliance_flagged_count"] >= 1


def test_compliance_dashboard_excludes_completed_engagement(admin_client):
    client = _create_client(admin_client, email="dash-completed@example.com")
    project = _create_project(
        admin_client, client["id"], name="Completed High Risk Co", risk_level="high"
    )
    admin_client.put(f"/projects/{project['id']}", json={"status": "completed"})

    resp = admin_client.get("/reports/dashboard/compliance")
    body = resp.json()
    assert not any(e["id"] == project["id"] for e in body["engagements"])


def test_compliance_dashboard_reports_overdue_task_count(admin_client):
    client = _create_client(admin_client, email="dash-overdue@example.com")
    project = _create_project(
        admin_client, client["id"], name="Overdue Risk Co", status="active", risk_level="high"
    )
    task_resp = admin_client.post(
        "/tasks/",
        json={
            "title": "Overdue compliance step",
            "client_id": client["id"],
            "project_id": project["id"],
            "due_date": "2000-01-01T00:00:00",
        },
    )
    assert task_resp.status_code in (200, 201), task_resp.text

    resp = admin_client.get("/reports/dashboard/compliance")
    body = resp.json()
    entry = next(e for e in body["engagements"] if e["id"] == project["id"])
    assert entry["overdue_task_count"] >= 1


def test_compliance_dashboard_lists_recent_risk_changes(admin_client):
    client = _create_client(admin_client, email="dash-recent@example.com")
    project = _create_project(
        admin_client, client["id"], name="Recent Change Co", status="active", risk_level="low"
    )
    admin_client.put(f"/projects/{project['id']}", json={"risk_level": "high"})

    resp = admin_client.get("/reports/dashboard/compliance")
    body = resp.json()
    assert any(c["project_id"] == project["id"] for c in body["recent_risk_changes"])
