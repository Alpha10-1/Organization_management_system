from tests.test_department_kpis import _create_user


def _create_manager_and_report(admin_client):
    manager = _create_user(admin_client, position="manager")
    report = _create_user(admin_client, manager_id=manager["id"])
    return manager, report


def _login_bearer(client, email, password="Sup3rSecret!"):
    """Logs in on the shared unauthenticated `client` fixture and returns a
    bearer token, rather than reusing admin_client (which would overwrite
    admin_client's own session cookie with this login)."""
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_create_leave_request_requires_manager(admin_client, client):
    user = _create_user(admin_client)  # no manager_id set
    token = _login_bearer(client, user["email"])

    resp = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_create_leave_request_routes_to_manager(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    token = _login_bearer(client, report["email"])

    resp = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2026-09-01", "end_date": "2026-09-05", "reason": "Vacation"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["approver_user_id"] == manager["id"]
    assert body["status"] == "pending"


def test_leave_request_rejects_invalid_type(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    token = _login_bearer(client, report["email"])

    resp = client.post(
        "/leave-requests/",
        json={"leave_type": "sabbatical", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_leave_request_rejects_backwards_dates(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    token = _login_bearer(client, report["email"])

    resp = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2026-09-05", "end_date": "2026-09-01"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_manager_can_approve_leave_request(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    report_token = _login_bearer(client, report["email"])
    create_resp = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers={"Authorization": f"Bearer {report_token}"},
    )
    leave_request = create_resp.json()

    manager_token = _login_bearer(client, manager["email"])
    resp = client.post(
        f"/leave-requests/{leave_request['id']}/approve",
        json={"notes": "Enjoy!"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
    assert resp.json()["decision_notes"] == "Enjoy!"


def test_non_manager_cannot_approve_leave_request(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    other_user = _create_user(admin_client)

    report_token = _login_bearer(client, report["email"])
    create_resp = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers={"Authorization": f"Bearer {report_token}"},
    )
    leave_request = create_resp.json()

    other_token = _login_bearer(client, other_user["email"])
    resp = client.post(
        f"/leave-requests/{leave_request['id']}/approve",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403


def test_admin_can_approve_any_leave_request(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    report_token = _login_bearer(client, report["email"])
    leave_request = client.post(
        "/leave-requests/",
        json={"leave_type": "sick", "start_date": "2026-09-01", "end_date": "2026-09-02"},
        headers={"Authorization": f"Bearer {report_token}"},
    ).json()

    resp = admin_client.post(f"/leave-requests/{leave_request['id']}/approve")
    assert resp.status_code == 200, resp.text


def test_requester_can_cancel_pending_request(admin_client, client):
    manager, report = _create_manager_and_report(admin_client)
    report_token = _login_bearer(client, report["email"])
    leave_request = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2026-09-01", "end_date": "2026-09-02"},
        headers={"Authorization": f"Bearer {report_token}"},
    ).json()

    resp = client.delete(
        f"/leave-requests/{leave_request['id']}", headers={"Authorization": f"Bearer {report_token}"}
    )
    assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/leave-requests/{leave_request['id']}")
    assert resp.status_code == 404  # soft-deleted, same as other entities in this codebase
