from tests.conftest import STAFF_EMAIL
from tests.test_department_kpis import _create_department, _create_user
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _setup(admin_client, prefix):
    requesting_dept = _create_department(admin_client)
    providing_dept = _create_department(admin_client)
    specialist = _create_user(admin_client, department_id=providing_dept["id"])
    client = _create_client(admin_client, email=f"{prefix}@example.com")
    project = _create_project(admin_client, client["id"])
    return requesting_dept, providing_dept, specialist, project


def _create_request(admin_client, requesting_dept, providing_dept, project, **overrides):
    payload = {
        "requesting_department_id": requesting_dept["id"],
        "providing_department_id": providing_dept["id"],
        "project_id": project["id"],
        "role_needed": "Specialist reviewer",
        "allocation_percent": 25,
    }
    payload.update(overrides)
    resp = admin_client.post("/resource-requests/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_resource_request(admin_client):
    requesting_dept, providing_dept, specialist, project = _setup(admin_client, "rr-create")
    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )
    assert request["status"] == "pending"
    assert request["requested_user_id"] == specialist["id"]


def test_resource_request_rejects_same_department(admin_client):
    dept = _create_department(admin_client)
    client = _create_client(admin_client, email="rr-same@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.post(
        "/resource-requests/",
        json={"requesting_department_id": dept["id"], "providing_department_id": dept["id"], "project_id": project["id"]},
    )
    assert resp.status_code == 400


def test_resource_request_rejects_user_outside_providing_department(admin_client):
    requesting_dept, providing_dept, _specialist, project = _setup(admin_client, "rr-mismatch")
    outsider = _create_user(admin_client)  # no department

    resp = admin_client.post(
        "/resource-requests/",
        json={
            "requesting_department_id": requesting_dept["id"],
            "providing_department_id": providing_dept["id"],
            "project_id": project["id"],
            "requested_user_id": outsider["id"],
        },
    )
    assert resp.status_code == 400


def test_approve_resource_request_creates_assignment(admin_client):
    requesting_dept, providing_dept, specialist, project = _setup(admin_client, "rr-approve")
    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )

    resp = admin_client.post(f"/resource-requests/{request['id']}/approve")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"

    assignments = admin_client.get(f"/projects/{project['id']}/assignments").json()
    assert any(a["user_id"] == specialist["id"] for a in assignments)


def test_only_providing_department_head_or_admin_can_approve(staff_client, admin_client):
    requesting_dept, providing_dept, specialist, project = _setup(admin_client, "rr-perm")
    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )

    resp = staff_client.post(f"/resource-requests/{request['id']}/approve")
    assert resp.status_code == 403


def test_providing_department_head_can_approve(admin_client, staff_client):
    requesting_dept = _create_department(admin_client)
    staff_users = admin_client.get("/users/").json()
    head = next(u for u in staff_users if u["email"] == STAFF_EMAIL)
    providing_dept = _create_department(admin_client, department_head_user_id=head["id"])
    specialist = _create_user(admin_client, department_id=providing_dept["id"])
    client = _create_client(admin_client, email="rr-head-approve@example.com")
    project = _create_project(admin_client, client["id"])

    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )

    resp = staff_client.post(f"/resource-requests/{request['id']}/approve")
    assert resp.status_code == 200, resp.text


def test_reject_resource_request(admin_client):
    requesting_dept, providing_dept, specialist, project = _setup(admin_client, "rr-reject")
    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )

    resp = admin_client.post(f"/resource-requests/{request['id']}/reject", json={"notes": "Not available"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    assignments = admin_client.get(f"/projects/{project['id']}/assignments").json()
    assert not any(a["user_id"] == specialist["id"] for a in assignments)


def test_cannot_approve_already_decided_request(admin_client):
    requesting_dept, providing_dept, specialist, project = _setup(admin_client, "rr-double")
    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )
    admin_client.post(f"/resource-requests/{request['id']}/approve")

    resp = admin_client.post(f"/resource-requests/{request['id']}/approve")
    assert resp.status_code == 400


def test_cancel_resource_request(admin_client):
    requesting_dept, providing_dept, specialist, project = _setup(admin_client, "rr-cancel")
    request = _create_request(
        admin_client, requesting_dept, providing_dept, project, requested_user_id=specialist["id"]
    )

    resp = admin_client.delete(f"/resource-requests/{request['id']}")
    assert resp.status_code == 200

    resp = admin_client.get(f"/resource-requests/{request['id']}")
    assert resp.status_code == 404
