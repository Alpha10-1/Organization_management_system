from tests.conftest import ADMIN_EMAIL, STAFF_EMAIL
from tests.test_client_types_and_assignments import _user_id
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_staffing import _create_user


# --- allocation_percent on assignments --------------------------------------


def test_assign_individual_with_allocation_percent(admin_client):
    client = _create_client(admin_client, email="alloc-user@example.com")
    project = _create_project(admin_client, client["id"], status="active")
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": staff_id, "allocation_percent": 60},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["allocation_percent"] == 60


def test_allocation_percent_rejected_for_department_assignment(admin_client):
    client = _create_client(admin_client, email="alloc-dept@example.com")
    project = _create_project(admin_client, client["id"], status="active")
    dept = admin_client.post("/departments/", json={"name": "Alloc Dept"}).json()

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"department_id": dept["id"], "allocation_percent": 50},
    )
    assert resp.status_code == 422


def test_allocation_percent_out_of_range_rejected(admin_client):
    client = _create_client(admin_client, email="alloc-range@example.com")
    project = _create_project(admin_client, client["id"], status="active")
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": staff_id, "allocation_percent": 150},
    )
    assert resp.status_code == 422


def test_update_assignment_allocation_percent(admin_client):
    client = _create_client(admin_client, email="alloc-update@example.com")
    project = _create_project(admin_client, client["id"], status="active")
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    created = admin_client.post(
        f"/projects/{project['id']}/assignments", json={"user_id": staff_id, "allocation_percent": 30}
    ).json()

    resp = admin_client.put(
        f"/projects/{project['id']}/assignments/{created['id']}", json={"allocation_percent": 80}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["allocation_percent"] == 80


# --- Capacity dashboard -------------------------------------------------------


def test_capacity_dashboard_sums_allocation_across_engagements(admin_client):
    person = _create_user(admin_client, position="senior_associate")
    client_a = _create_client(admin_client, email="cap-a@example.com")
    client_b = _create_client(admin_client, email="cap-b@example.com")
    project_a = _create_project(admin_client, client_a["id"], name="Cap Project A", status="active")
    project_b = _create_project(admin_client, client_b["id"], name="Cap Project B", status="active")

    admin_client.post(
        f"/projects/{project_a['id']}/assignments",
        json={"user_id": person["id"], "allocation_percent": 40},
    )
    admin_client.post(
        f"/projects/{project_b['id']}/assignments",
        json={"user_id": person["id"], "allocation_percent": 30},
    )

    resp = admin_client.get("/reports/dashboard/capacity")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    entry = next(p for p in body["people"] if p["id"] == person["id"])
    assert entry["total_allocated_percent"] == 70
    assert entry["status"] == "fully_allocated"
    assert len(entry["engagements"]) == 2


def test_capacity_dashboard_flags_over_allocated(admin_client):
    person = _create_user(admin_client, position="manager")
    client_a = _create_client(admin_client, email="cap-over-a@example.com")
    client_b = _create_client(admin_client, email="cap-over-b@example.com")
    project_a = _create_project(admin_client, client_a["id"], name="Over A", status="active")
    project_b = _create_project(admin_client, client_b["id"], name="Over B", status="active")

    admin_client.post(
        f"/projects/{project_a['id']}/assignments",
        json={"user_id": person["id"], "allocation_percent": 70},
    )
    admin_client.post(
        f"/projects/{project_b['id']}/assignments",
        json={"user_id": person["id"], "allocation_percent": 60},
    )

    resp = admin_client.get("/reports/dashboard/capacity")
    body = resp.json()
    entry = next(p for p in body["people"] if p["id"] == person["id"])
    assert entry["total_allocated_percent"] == 130
    assert entry["status"] == "over_allocated"
    assert body["over_allocated_count"] >= 1


def test_capacity_dashboard_flags_under_allocated(admin_client):
    person = _create_user(admin_client, position="associate")
    client = _create_client(admin_client, email="cap-under@example.com")
    project = _create_project(admin_client, client["id"], name="Under Project", status="active")

    admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": person["id"], "allocation_percent": 20},
    )

    resp = admin_client.get("/reports/dashboard/capacity")
    body = resp.json()
    entry = next(p for p in body["people"] if p["id"] == person["id"])
    assert entry["status"] == "under_allocated"


def test_capacity_dashboard_flags_bench_for_no_assignments(admin_client):
    person = _create_user(admin_client, position="associate")

    resp = admin_client.get("/reports/dashboard/capacity")
    body = resp.json()
    entry = next(p for p in body["people"] if p["id"] == person["id"])
    assert entry["status"] == "bench"
    assert entry["total_allocated_percent"] == 0
    assert body["bench_count"] >= 1


def test_capacity_dashboard_ignores_completed_engagements(admin_client):
    person = _create_user(admin_client, position="director")
    client = _create_client(admin_client, email="cap-completed@example.com")
    project = _create_project(admin_client, client["id"], name="Completed Cap Project", status="active")

    admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": person["id"], "allocation_percent": 90},
    )
    admin_client.put(f"/projects/{project['id']}", json={"status": "completed"})

    resp = admin_client.get("/reports/dashboard/capacity")
    body = resp.json()
    entry = next(p for p in body["people"] if p["id"] == person["id"])
    assert entry["total_allocated_percent"] == 0
    assert entry["status"] == "bench"


def test_capacity_dashboard_excludes_disabled_users(admin_client):
    person = _create_user(admin_client, position="associate")
    admin_client.patch(f"/users/{person['email']}/status", json={"disabled": True})

    resp = admin_client.get("/reports/dashboard/capacity")
    body = resp.json()
    assert not any(p["id"] == person["id"] for p in body["people"])


def test_capacity_dashboard_tracks_unspecified_allocation(admin_client):
    person = _create_user(admin_client, position="senior_associate")
    client = _create_client(admin_client, email="cap-unspecified@example.com")
    project = _create_project(admin_client, client["id"], name="Unspecified Cap", status="active")

    admin_client.post(
        f"/projects/{project['id']}/assignments", json={"user_id": person["id"]}
    )

    resp = admin_client.get("/reports/dashboard/capacity")
    body = resp.json()
    entry = next(p for p in body["people"] if p["id"] == person["id"])
    assert entry["unspecified_allocation_count"] == 1
    assert entry["total_allocated_percent"] == 0
