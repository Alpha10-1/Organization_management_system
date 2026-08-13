from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, STAFF_EMAIL, STAFF_PASSWORD
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _second_client(email: str, password: str) -> TestClient:
    """A genuinely independent TestClient (own cookie jar), needed whenever
    a single test acts as two different logged-in users -- the admin_client
    and staff_client fixtures share one cookie jar under the hood, so the
    second login silently overwrites the first."""
    c = TestClient(app)
    resp = c.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return c


def _create_time_entry(client, project_id, **overrides):
    payload = {
        "project_id": project_id,
        "hours": "2.5",
        "entry_date": "2026-08-01",
        "billable": True,
    }
    payload.update(overrides)
    resp = client.post("/time-entries/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- CRUD -----------------------------------------------------------------


def test_create_and_get_time_entry(admin_client):
    client = _create_client(admin_client, email="time-basic@example.com")
    project = _create_project(admin_client, client["id"])

    entry = _create_time_entry(admin_client, project["id"], notes="Kickoff prep")
    assert entry["project_id"] == project["id"]
    assert entry["hours"] == "2.50"
    assert entry["billable"] is True
    assert entry["user_email"] == ADMIN_EMAIL

    resp = admin_client.get(f"/time-entries/{entry['id']}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["notes"] == "Kickoff prep"


def test_time_entry_requires_valid_project(admin_client):
    resp = admin_client.post(
        "/time-entries/",
        json={"project_id": 999999, "hours": "1.0", "entry_date": "2026-08-01"},
    )
    assert resp.status_code == 404


def test_time_entry_rejects_hours_out_of_range(admin_client):
    client = _create_client(admin_client, email="time-range@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.post(
        "/time-entries/",
        json={"project_id": project["id"], "hours": "0", "entry_date": "2026-08-01"},
    )
    assert resp.status_code == 422

    resp = admin_client.post(
        "/time-entries/",
        json={"project_id": project["id"], "hours": "30", "entry_date": "2026-08-01"},
    )
    assert resp.status_code == 422


def test_time_entry_task_must_belong_to_project(admin_client):
    client = _create_client(admin_client, email="time-task@example.com")
    project = _create_project(admin_client, client["id"])
    other_project = _create_project(admin_client, client["id"], name="Other Engagement")

    task_resp = admin_client.post(
        "/tasks/", json={"title": "Fieldwork", "project_id": other_project["id"]}
    )
    task = task_resp.json()

    resp = admin_client.post(
        "/time-entries/",
        json={
            "project_id": project["id"],
            "task_id": task["id"],
            "hours": "1.0",
            "entry_date": "2026-08-01",
        },
    )
    assert resp.status_code == 400


def test_time_entry_with_matching_task_succeeds(admin_client):
    client = _create_client(admin_client, email="time-task-ok@example.com")
    project = _create_project(admin_client, client["id"])
    task = admin_client.post("/tasks/", json={"title": "Fieldwork", "project_id": project["id"]}).json()

    entry = _create_time_entry(admin_client, project["id"], task_id=task["id"], hours="3.0")
    assert entry["task_id"] == task["id"]


def test_update_and_delete_own_time_entry(admin_client):
    client = _create_client(admin_client, email="time-update@example.com")
    project = _create_project(admin_client, client["id"])
    entry = _create_time_entry(admin_client, project["id"])

    resp = admin_client.put(f"/time-entries/{entry['id']}", json={"hours": "4.0", "billable": False})
    assert resp.status_code == 200, resp.text
    assert resp.json()["hours"] == "4.00"
    assert resp.json()["billable"] is False

    resp = admin_client.delete(f"/time-entries/{entry['id']}")
    assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/time-entries/{entry['id']}")
    assert resp.status_code == 404


def test_staff_cannot_edit_others_time_entry(admin_client):
    client = _create_client(admin_client, email="time-perm@example.com")
    project = _create_project(admin_client, client["id"])
    entry = _create_time_entry(admin_client, project["id"])

    staff = _second_client(STAFF_EMAIL, STAFF_PASSWORD)
    resp = staff.put(f"/time-entries/{entry['id']}", json={"hours": "1.0"})
    assert resp.status_code == 403

    resp = staff.delete(f"/time-entries/{entry['id']}")
    assert resp.status_code == 403


def test_staff_cannot_log_time_for_another_user(admin_client):
    client = _create_client(admin_client, email="time-onbehalf@example.com")
    project = _create_project(admin_client, client["id"])

    staff = _second_client(STAFF_EMAIL, STAFF_PASSWORD)
    resp = staff.post(
        "/time-entries/",
        json={
            "project_id": project["id"],
            "hours": "1.0",
            "entry_date": "2026-08-01",
            "user_email": ADMIN_EMAIL,
        },
    )
    assert resp.status_code == 403


def test_admin_can_log_time_for_another_user(admin_client):
    client = _create_client(admin_client, email="time-admin-onbehalf@example.com")
    project = _create_project(admin_client, client["id"])

    entry = _create_time_entry(admin_client, project["id"], user_email=STAFF_EMAIL)
    assert entry["user_email"] == STAFF_EMAIL


# --- Filtering & utilization -----------------------------------------------


def test_list_time_entries_filters_by_project_and_billable(admin_client):
    client = _create_client(admin_client, email="time-filter@example.com")
    project = _create_project(admin_client, client["id"])
    other_project = _create_project(admin_client, client["id"], name="Other")

    _create_time_entry(admin_client, project["id"], hours="2.0", billable=True)
    _create_time_entry(admin_client, project["id"], hours="1.0", billable=False)
    _create_time_entry(admin_client, other_project["id"], hours="5.0")

    resp = admin_client.get(f"/time-entries/?project_id={project['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = admin_client.get(f"/time-entries/?project_id={project['id']}&billable=true")
    assert len(resp.json()) == 1
    assert resp.json()[0]["billable"] is True


def test_project_utilization_summary(admin_client):
    client = _create_client(admin_client, email="time-util@example.com")
    project = _create_project(admin_client, client["id"], budget="10000.00")

    _create_time_entry(admin_client, project["id"], hours="3.0", billable=True)
    _create_time_entry(admin_client, project["id"], hours="1.5", billable=False)

    resp = admin_client.get(f"/time-entries/summary?project_id={project['id']}")
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert summary["total_hours"] == "4.50"
    assert summary["billable_hours"] == "3.00"
    assert summary["non_billable_hours"] == "1.50"
    assert summary["entry_count"] == 2
    assert summary["budget"] == "10000.00"


def test_project_utilization_summary_requires_valid_project(admin_client):
    resp = admin_client.get("/time-entries/summary?project_id=999999")
    assert resp.status_code == 404
