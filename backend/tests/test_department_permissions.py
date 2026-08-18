from tests.conftest import STAFF_EMAIL, STAFF_PASSWORD
from tests.test_contracts import _create_contract
from tests.test_department_kpis import _create_department, _create_user
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _login_bearer(client, email, password="Sup3rSecret!"):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(client, email, password="Sup3rSecret!"):
    return {"Authorization": f"Bearer {_login_bearer(client, email, password)}"}


# --- Unscoped entities stay open to any staff member -----------------------------


def test_unscoped_client_is_writable_by_any_staff(admin_client, client, staff_client):
    # No department_id set -> unscoped -> staff_client (not admin, no department) can still write.
    resp = staff_client.post(
        "/clients/",
        json={"client_type": "individual", "first_name": "Uns", "last_name": "Coped", "email": "unscoped-client@example.com"},
    )
    assert resp.status_code == 200, resp.text


# --- Scoped clients: cross-department staff blocked, same-department allowed -----


def test_staff_outside_department_cannot_create_client_in_it(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)  # no department

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/clients/",
        json={
            "client_type": "individual",
            "first_name": "Blocked",
            "last_name": "Client",
            "email": "blocked-client@example.com",
            "department_id": dept["id"],
        },
        headers=headers,
    )
    assert resp.status_code == 403


def test_staff_in_department_can_create_client_in_it(admin_client, client):
    dept = _create_department(admin_client)
    member = _create_user(admin_client, department_id=dept["id"])

    headers = _auth_headers(client, member["email"])
    resp = client.post(
        "/clients/",
        json={
            "client_type": "individual",
            "first_name": "Allowed",
            "last_name": "Client",
            "email": "allowed-client@example.com",
            "department_id": dept["id"],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_department_head_can_create_client_in_own_department(admin_client, client):
    head = _create_user(admin_client)
    dept = _create_department(admin_client, department_head_user_id=head["id"])

    headers = _auth_headers(client, head["email"])
    resp = client.post(
        "/clients/",
        json={
            "client_type": "individual",
            "first_name": "Head",
            "last_name": "Managed",
            "email": "head-managed-client@example.com",
            "department_id": dept["id"],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_admin_bypasses_department_scoping(admin_client):
    dept = _create_department(admin_client)
    resp = admin_client.post(
        "/clients/",
        json={
            "client_type": "individual",
            "first_name": "Admin",
            "last_name": "Created",
            "email": "admin-created-client@example.com",
            "department_id": dept["id"],
        },
    )
    assert resp.status_code == 200, resp.text


def test_staff_can_view_client_outside_department_but_not_edit(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="view-only@example.com", department_id=dept["id"])

    headers = _auth_headers(client, outsider["email"])

    # Read access is unrestricted.
    resp = client.get(f"/clients/{scoped_client['id']}", headers=headers)
    assert resp.status_code == 200

    # Write access is not.
    resp = client.put(f"/clients/{scoped_client['id']}", json={"first_name": "Hacked"}, headers=headers)
    assert resp.status_code == 403


def test_client_reassignment_requires_access_to_both_departments(admin_client, client):
    dept_a = _create_department(admin_client)
    dept_b = _create_department(admin_client)
    member_a = _create_user(admin_client, department_id=dept_a["id"])
    scoped_client = _create_client(admin_client, email="reassign@example.com", department_id=dept_a["id"])

    headers = _auth_headers(client, member_a["email"])
    resp = client.put(
        f"/clients/{scoped_client['id']}", json={"department_id": dept_b["id"]}, headers=headers
    )
    assert resp.status_code == 403  # member of dept_a has no access to dept_b


# --- Projects follow their client's department ------------------------------------


def test_project_write_scoped_via_client_department(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="proj-scope@example.com", department_id=dept["id"])

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/projects/",
        json={"client_id": scoped_client["id"], "name": "Blocked Engagement", "type": "audit"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_project_write_allowed_for_department_member(admin_client, client):
    dept = _create_department(admin_client)
    member = _create_user(admin_client, department_id=dept["id"])
    scoped_client = _create_client(admin_client, email="proj-allowed@example.com", department_id=dept["id"])

    headers = _auth_headers(client, member["email"])
    resp = client.post(
        "/projects/",
        json={"client_id": scoped_client["id"], "name": "Allowed Engagement", "type": "audit"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_unscoped_project_is_writable_by_any_staff(admin_client, client, staff_client):
    unscoped_client = _create_client(admin_client, email="proj-unscoped@example.com")  # no department
    headers = _auth_headers(client, STAFF_EMAIL, STAFF_PASSWORD)
    resp = client.post(
        "/projects/",
        json={"client_id": unscoped_client["id"], "name": "Unscoped Engagement", "type": "audit"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


# --- Tasks follow their project/client department, with an assignee carve-out -----


def test_task_write_scoped_via_project_department(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="task-scope@example.com", department_id=dept["id"])
    project = _create_project(admin_client, scoped_client["id"])

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/tasks/", json={"title": "Blocked task", "project_id": project["id"]}, headers=headers
    )
    assert resp.status_code == 403


def test_unscoped_task_is_writable_by_any_staff(admin_client, client):
    outsider = _create_user(admin_client)
    headers = _auth_headers(client, outsider["email"])
    resp = client.post("/tasks/", json={"title": "Freestanding onboarding task"}, headers=headers)
    assert resp.status_code == 200, resp.text


def test_task_assignee_can_update_own_task_outside_department(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)  # borrowed specialist, no department membership
    scoped_client = _create_client(admin_client, email="task-assignee@example.com", department_id=dept["id"])
    project = _create_project(admin_client, scoped_client["id"])

    task = admin_client.post(
        "/tasks/",
        json={"title": "Loaned specialist task", "project_id": project["id"], "assigned_to_email": outsider["email"]},
    ).json()

    headers = _auth_headers(client, outsider["email"])
    resp = client.put(f"/tasks/{task['id']}", json={"status": "in_progress"}, headers=headers)
    assert resp.status_code == 200, resp.text


def test_non_assignee_outsider_cannot_update_scoped_task(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="task-nonassignee@example.com", department_id=dept["id"])
    project = _create_project(admin_client, scoped_client["id"])
    task = admin_client.post("/tasks/", json={"title": "Someone else's task", "project_id": project["id"]}).json()

    headers = _auth_headers(client, outsider["email"])
    resp = client.put(f"/tasks/{task['id']}", json={"status": "in_progress"}, headers=headers)
    assert resp.status_code == 403


# --- Contracts, milestones, change orders follow project department --------------


def test_contract_write_scoped_via_project_department(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="contract-scope@example.com", department_id=dept["id"])
    project = _create_project(admin_client, scoped_client["id"])

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/contracts/",
        json={"project_id": project["id"], "name": "Blocked contract", "billing_type": "fixed_fee", "value": "1000.00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_milestone_write_scoped_via_project_department(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="milestone-scope@example.com", department_id=dept["id"])
    project = _create_project(admin_client, scoped_client["id"])

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/milestones/", json={"project_id": project["id"], "name": "Blocked milestone"}, headers=headers
    )
    assert resp.status_code == 403


def test_change_order_write_scoped_via_contract_department(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)
    scoped_client = _create_client(admin_client, email="co-scope@example.com", department_id=dept["id"])
    project = _create_project(admin_client, scoped_client["id"])
    contract = _create_contract(admin_client, project["id"])

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/change-orders/",
        json={"contract_id": contract["id"], "title": "Blocked change order", "change_type": "scope_change"},
        headers=headers,
    )
    assert resp.status_code == 403


# --- Task templates follow their own department_id --------------------------------


def test_department_scoped_template_blocks_outsiders(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/task-templates/",
        json={"name": "Blocked template", "department_id": dept["id"], "items": []},
        headers=headers,
    )
    assert resp.status_code == 403


def test_firm_wide_template_open_to_any_staff(admin_client, client):
    outsider = _create_user(admin_client)
    headers = _auth_headers(client, outsider["email"])
    resp = client.post("/task-templates/", json={"name": "Firm-wide template", "items": []}, headers=headers)
    assert resp.status_code == 200, resp.text
