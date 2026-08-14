from tests.conftest import ADMIN_EMAIL
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _upload_file(admin_client, filename="deliverable.txt", content=b"hello", client_id=None, project_id=None):
    files = {"file": (filename, content, "text/plain")}
    data = {}
    if client_id is not None:
        data["client_id"] = str(client_id)
    if project_id is not None:
        data["project_id"] = str(project_id)
    resp = admin_client.post("/files/upload", files=files, data=data)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Document scoping to projects ------------------------------------------


def test_upload_file_scoped_to_project(admin_client):
    client = _create_client(admin_client, email="doc-client@example.com")
    project = _create_project(admin_client, client["id"])

    uploaded = _upload_file(admin_client, project_id=project["id"])
    assert uploaded["project_id"] == project["id"]


def test_list_files_filters_by_project(admin_client):
    client = _create_client(admin_client, email="doc-filter@example.com")
    project_a = _create_project(admin_client, client["id"], name="Engagement A")
    project_b = _create_project(admin_client, client["id"], name="Engagement B")

    file_a = _upload_file(admin_client, filename="a.txt", project_id=project_a["id"])
    _upload_file(admin_client, filename="b.txt", project_id=project_b["id"])

    resp = admin_client.get(f"/files/?project_id={project_a['id']}")
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()]
    assert file_a["id"] in ids
    assert len(ids) == 1


def test_upload_file_rejects_unknown_project(admin_client):
    resp = admin_client.post(
        "/files/upload",
        files={"file": ("x.txt", b"data", "text/plain")},
        data={"project_id": "999999"},
    )
    assert resp.status_code == 404


# --- Dashboards --------------------------------------------------------


def test_partner_dashboard_reports_engagements_and_deadlines(admin_client):
    client = _create_client(admin_client, email="partner-dash@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        name="Partner Led Audit",
        engagement_partner_email=ADMIN_EMAIL,
        status="active",
    )

    admin_client.post(
        "/tasks/",
        json={
            "title": "Overdue deliverable",
            "project_id": project["id"],
            "due_date": "2020-01-01T00:00:00",
        },
    )
    admin_client.post(
        "/time-entries/",
        json={"project_id": project["id"], "hours": 4, "entry_date": "2026-01-10", "billable": True},
    )

    resp = admin_client.get(f"/reports/dashboard/partner?partner_email={ADMIN_EMAIL}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["active_engagement_count"] == 1
    assert body["overdue_task_count"] == 1
    assert body["engagements"][0]["hours_logged"] == 4.0


def test_client_dashboard_reports_health_and_contracts(admin_client):
    client = _create_client(admin_client, email="client-dash@example.com")
    project = _create_project(admin_client, client["id"], status="active")

    admin_client.post(
        "/contracts/",
        json={
            "project_id": project["id"],
            "name": "Engagement Letter",
            "billing_type": "fixed_fee",
            "value": "25000.00",
            "status": "signed",
        },
    )

    resp = admin_client.get(f"/reports/dashboard/client/{client['id']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["active_engagement_count"] == 1
    assert len(body["contracts"]) == 1
    assert body["relationship_health"] in {"green", "amber", "red"}


def test_client_dashboard_rejects_unknown_client(admin_client):
    resp = admin_client.get("/reports/dashboard/client/999999")
    assert resp.status_code == 404
