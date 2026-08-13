from tests.test_new_features import _create_client


def _create_project(admin_client, client_id, **overrides):
    payload = {
        "client_id": client_id,
        "name": "FY26 External Audit",
        "type": "audit",
        "status": "planning",
        "risk_level": "medium",
    }
    payload.update(overrides)
    resp = admin_client.post("/projects/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- CRUD -------------------------------------------------------------


def test_create_and_get_project(admin_client):
    client = _create_client(admin_client, email="acme-audit@example.com")
    project = _create_project(admin_client, client["id"], name="Acme FY26 Audit")

    assert project["name"] == "Acme FY26 Audit"
    assert project["client_id"] == client["id"]
    assert project["status"] == "planning"
    assert project["risk_level"] == "medium"
    assert project["created_by_email"]

    resp = admin_client.get(f"/projects/{project['id']}")
    assert resp.status_code == 200, resp.text
    fetched = resp.json()
    assert fetched["id"] == project["id"]
    assert fetched["task_count"] == 0


def test_create_project_rejects_unknown_client(admin_client):
    resp = admin_client.post(
        "/projects/", json={"client_id": 999999, "name": "Ghost Engagement", "type": "audit"}
    )
    assert resp.status_code == 404


def test_create_project_rejects_invalid_type(admin_client):
    client = _create_client(admin_client, email="badtype@example.com")
    resp = admin_client.post(
        "/projects/", json={"client_id": client["id"], "name": "Bad Type", "type": "not-a-type"}
    )
    assert resp.status_code == 400


def test_create_project_rejects_end_before_start(admin_client):
    client = _create_client(admin_client, email="baddates@example.com")
    resp = admin_client.post(
        "/projects/",
        json={
            "client_id": client["id"],
            "name": "Backwards Dates",
            "type": "tax",
            "start_date": "2026-06-01T00:00:00",
            "end_date": "2026-01-01T00:00:00",
        },
    )
    assert resp.status_code == 400


def test_update_project_status_and_activity_log(admin_client):
    client = _create_client(admin_client, email="statuschange@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.put(f"/projects/{project['id']}", json={"status": "active"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"


def test_soft_delete_project_excludes_from_list(admin_client):
    client = _create_client(admin_client, email="deleteme@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.delete(f"/projects/{project['id']}")
    assert resp.status_code == 200, resp.text

    listed = admin_client.get(f"/projects/?client_id={client['id']}").json()
    assert all(p["id"] != project["id"] for p in listed)

    resp = admin_client.get(f"/projects/{project['id']}")
    assert resp.status_code == 404


def test_list_projects_filters_by_status_and_type(admin_client):
    client = _create_client(admin_client, email="filters@example.com")
    audit = _create_project(admin_client, client["id"], name="Audit Engagement", type="audit")
    tax = _create_project(admin_client, client["id"], name="Tax Engagement", type="tax", status="active")

    audit_only = admin_client.get("/projects/?type=audit").json()
    assert any(p["id"] == audit["id"] for p in audit_only)
    assert all(p["id"] != tax["id"] for p in audit_only)

    active_only = admin_client.get("/projects/?status=active").json()
    assert any(p["id"] == tax["id"] for p in active_only)


# --- Task <-> Project linking -------------------------------------------


def test_task_can_be_created_with_project_id(admin_client):
    client = _create_client(admin_client, email="task-link@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.post(
        "/tasks/",
        json={"title": "Kickoff meeting", "client_id": client["id"], "project_id": project["id"]},
    )
    assert resp.status_code == 200, resp.text
    task = resp.json()
    assert task["project_id"] == project["id"]

    # Rollup counts should reflect the new task.
    fetched = admin_client.get(f"/projects/{project['id']}").json()
    assert fetched["task_count"] == 1
    assert fetched["open_task_count"] == 1


def test_task_rejects_unknown_project(admin_client):
    resp = admin_client.post("/tasks/", json={"title": "Orphan task", "project_id": 999999})
    assert resp.status_code == 404


def test_task_rejects_client_mismatch_with_project(admin_client):
    client_a = _create_client(admin_client, email="client-a@example.com")
    client_b = _create_client(admin_client, email="client-b@example.com")
    project = _create_project(admin_client, client_a["id"])

    resp = admin_client.post(
        "/tasks/",
        json={"title": "Mismatched task", "client_id": client_b["id"], "project_id": project["id"]},
    )
    assert resp.status_code == 400


def test_tasks_can_be_filtered_by_project(admin_client):
    client = _create_client(admin_client, email="filter-tasks@example.com")
    project = _create_project(admin_client, client["id"])
    other_project = _create_project(admin_client, client["id"], name="Other Engagement")

    admin_client.post("/tasks/", json={"title": "In scope", "project_id": project["id"]})
    admin_client.post("/tasks/", json={"title": "Out of scope", "project_id": other_project["id"]})

    resp = admin_client.get(f"/tasks/?project_id={project['id']}")
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "In scope" in titles
    assert "Out of scope" not in titles


def test_project_overdue_task_rollup(admin_client):
    client = _create_client(admin_client, email="overdue@example.com")
    project = _create_project(admin_client, client["id"])

    admin_client.post(
        "/tasks/",
        json={
            "title": "Overdue deliverable",
            "project_id": project["id"],
            "due_date": "2020-01-01T00:00:00",
        },
    )

    fetched = admin_client.get(f"/projects/{project['id']}").json()
    assert fetched["overdue_task_count"] == 1


def test_staff_can_create_project(staff_client):
    client = _create_client(staff_client, email="staff-created@example.com")
    project = _create_project(staff_client, client["id"])
    assert project["status"] == "planning"
