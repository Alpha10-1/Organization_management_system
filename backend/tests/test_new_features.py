from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, STAFF_EMAIL, STAFF_PASSWORD


def _login(username, password):
    """admin_client and staff_client share one TestClient/cookie jar (see
    conftest.py), so using both together in one test means the second
    login silently overwrites the first. Tests that genuinely need two
    independent authenticated sessions build their own here instead."""
    c = TestClient(app)
    resp = c.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return c


def _create_client(admin_client, **overrides):
    payload = {
        "client_type": "individual",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "phone": "555-0100",
        "status": "Active",
    }
    payload.update(overrides)
    resp = admin_client.post("/clients/", json=payload)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# --- Departments ---------------------------------------------------------

def test_admin_can_create_and_list_department(admin_client):
    resp = admin_client.post("/departments/", json={"name": "Sales", "description": "Sales team"})
    assert resp.status_code == 200, resp.text
    dept = resp.json()
    assert dept["name"] == "Sales"

    listed = admin_client.get("/departments/").json()
    assert any(d["id"] == dept["id"] for d in listed)


def test_staff_cannot_create_department(staff_client):
    resp = staff_client.post("/departments/", json={"name": "Ops"})
    assert resp.status_code == 403


def test_client_can_be_filtered_by_department(admin_client):
    dept = admin_client.post("/departments/", json={"name": "Support"}).json()
    created = _create_client(admin_client, email="dept-client@example.com", department_id=dept["id"])

    resp = admin_client.get(f"/clients/?department_id={dept['id']}")
    assert resp.status_code == 200
    assert any(c["id"] == created["id"] for c in resp.json())


# --- Tags ------------------------------------------------------------------

def test_create_tag_and_assign_to_client(admin_client):
    tag = admin_client.post("/tags/", json={"name": "VIP", "color": "#ff0000"}).json()
    created = _create_client(admin_client, email="tagged@example.com")

    assign_resp = admin_client.post(f"/tags/clients/{created['id']}/{tag['id']}")
    assert assign_resp.status_code == 200

    client_tags = admin_client.get(f"/tags/clients/{created['id']}").json()
    assert any(t["id"] == tag["id"] for t in client_tags)

    remove_resp = admin_client.delete(f"/tags/clients/{created['id']}/{tag['id']}")
    assert remove_resp.status_code == 200
    assert admin_client.get(f"/tags/clients/{created['id']}").json() == []


def test_duplicate_tag_name_rejected(admin_client):
    admin_client.post("/tags/", json={"name": "Priority"})
    resp = admin_client.post("/tags/", json={"name": "Priority"})
    assert resp.status_code == 400


# --- Client notes history ---------------------------------------------------

def test_client_notes_history_keeps_multiple_entries(admin_client):
    created = _create_client(admin_client, email="notes@example.com")

    admin_client.post(f"/clients/{created['id']}/notes", json={"body": "First note"})
    admin_client.post(f"/clients/{created['id']}/notes", json={"body": "Second note"})

    notes = admin_client.get(f"/clients/{created['id']}/notes").json()
    assert len(notes) == 2
    bodies = {n["body"] for n in notes}
    assert bodies == {"First note", "Second note"}


def test_delete_own_note(admin_client):
    created = _create_client(admin_client, email="notes2@example.com")
    note = admin_client.post(f"/clients/{created['id']}/notes", json={"body": "temp"}).json()

    del_resp = admin_client.delete(f"/clients/{created['id']}/notes/{note['id']}")
    assert del_resp.status_code == 200

    notes = admin_client.get(f"/clients/{created['id']}/notes").json()
    assert notes == []


# --- Bulk client status update ---------------------------------------------

def test_bulk_status_update(admin_client):
    c1 = _create_client(admin_client, email="bulk1@example.com")
    c2 = _create_client(admin_client, email="bulk2@example.com")

    resp = admin_client.post(
        "/clients/bulk/status", json={"client_ids": [c1["id"], c2["id"]], "status": "Closed"}
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2

    for cid in (c1["id"], c2["id"]):
        fetched = admin_client.get(f"/clients/{cid}").json()
        assert fetched["status"] == "Closed"


def test_bulk_status_update_rejects_invalid_status(admin_client):
    c1 = _create_client(admin_client, email="bulk3@example.com")
    resp = admin_client.post("/clients/bulk/status", json={"client_ids": [c1["id"]], "status": "Bogus"})
    assert resp.status_code == 400


# --- Tasks -------------------------------------------------------------------

def test_create_task_and_assign_notifies_assignee(admin_client):
    resp = admin_client.post(
        "/tasks/",
        json={"title": "Follow up with client", "assigned_to_email": STAFF_EMAIL, "priority": "high"},
    )
    assert resp.status_code == 200, resp.text
    task = resp.json()
    assert task["assigned_to_email"] == STAFF_EMAIL
    assert task["status"] == "open"

    staff = _login(STAFF_EMAIL, STAFF_PASSWORD)
    notifications = staff.get("/notifications/").json()
    assert any(n["type"] == "task_assigned" for n in notifications)


def test_update_task_status_to_done_sets_completed_at(admin_client):
    task = admin_client.post("/tasks/", json={"title": "Ship report"}).json()
    resp = admin_client.put(f"/tasks/{task['id']}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None


def test_task_invalid_priority_rejected(admin_client):
    resp = admin_client.post("/tasks/", json={"title": "Bad", "priority": "urgent!"})
    assert resp.status_code == 400


def test_delete_task(admin_client):
    task = admin_client.post("/tasks/", json={"title": "Temp task"}).json()
    resp = admin_client.delete(f"/tasks/{task['id']}")
    assert resp.status_code == 200

    listed = admin_client.get("/tasks/").json()
    assert all(t["id"] != task["id"] for t in listed)


# --- Notifications -------------------------------------------------------------

def test_mark_notification_read(admin_client):
    admin_client.post("/tasks/", json={"title": "Notify me", "assigned_to_email": STAFF_EMAIL})

    staff = _login(STAFF_EMAIL, STAFF_PASSWORD)
    unread = staff.get("/notifications/?unread_only=true").json()
    assert len(unread) >= 1

    notif_id = unread[0]["id"]
    resp = staff.patch(f"/notifications/{notif_id}/read")
    assert resp.status_code == 200

    still_unread = staff.get("/notifications/?unread_only=true").json()
    assert all(n["id"] != notif_id for n in still_unread)


def test_mark_all_notifications_read(admin_client):
    admin_client.post("/tasks/", json={"title": "Task A", "assigned_to_email": STAFF_EMAIL})
    admin_client.post("/tasks/", json={"title": "Task B", "assigned_to_email": STAFF_EMAIL})

    staff = _login(STAFF_EMAIL, STAFF_PASSWORD)
    resp = staff.patch("/notifications/read-all")
    assert resp.status_code == 200

    assert staff.get("/notifications/?unread_only=true").json() == []


# --- Comments / mentions -------------------------------------------------------

def test_comment_with_mention_notifies_user(admin_client):
    created = _create_client(admin_client, email="mentioned@example.com")

    resp = admin_client.post(
        "/comments/",
        json={
            "entity_type": "client",
            "entity_id": created["id"],
            "body": f"Please review this @{STAFF_EMAIL}",
        },
    )
    assert resp.status_code == 200, resp.text

    staff = _login(STAFF_EMAIL, STAFF_PASSWORD)
    notifications = staff.get("/notifications/").json()
    assert any(n["type"] == "mention" for n in notifications)


def test_list_comments_for_entity(admin_client):
    created = _create_client(admin_client, email="commented@example.com")
    admin_client.post(
        "/comments/", json={"entity_type": "client", "entity_id": created["id"], "body": "Note one"}
    )

    resp = admin_client.get(f"/comments/?entity_type=client&entity_id={created['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- Global search --------------------------------------------------------------

def test_global_search_finds_client(admin_client):
    _create_client(admin_client, first_name="Zaphod", last_name="Beeblebrox", email="zaphod@example.com")

    resp = admin_client.get("/search/?q=Zaphod")
    assert resp.status_code == 200
    body = resp.json()
    assert any("Zaphod" in c["label"] for c in body["clients"])


# --- Reports / exports ------------------------------------------------------------

def test_export_clients_csv(admin_client):
    _create_client(admin_client, email="csv-export@example.com")
    resp = admin_client.get("/reports/clients/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert b"csv-export@example.com" in resp.content


def test_export_clients_pdf(admin_client):
    _create_client(admin_client, email="pdf-export@example.com")
    resp = admin_client.get("/reports/clients/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_export_tasks_csv(admin_client):
    admin_client.post("/tasks/", json={"title": "Exportable task"})
    resp = admin_client.get("/reports/tasks/csv")
    assert resp.status_code == 200
    assert b"Exportable task" in resp.content


# --- Password reset & email verification -------------------------------------------

def test_password_reset_flow(client, admin_client):
    req = client.post("/auth/request-password-reset", json={"email": ADMIN_EMAIL})
    assert req.status_code == 200

    # Non-existent email gets the same generic response (no enumeration)
    req2 = client.post("/auth/request-password-reset", json={"email": "nobody@example.com"})
    assert req2.status_code == 200
    assert req2.json() == req.json()


def test_reset_password_with_invalid_token_fails(client):
    resp = client.post("/auth/reset-password", json={"token": "not-a-real-token", "new_password": "NewPass123!"})
    assert resp.status_code == 400


def test_request_verification_requires_auth(client):
    resp = client.post("/auth/request-verification")
    assert resp.status_code == 401


def test_verify_email_invalid_token_fails(client):
    resp = client.post("/auth/verify-email", json={"token": "bogus"})
    assert resp.status_code == 400


# --- File versioning and bulk file actions -----------------------------------

def _upload_file(admin_client, filename="report.txt", content=b"hello world", replaces_file_id=None):
    files = {"file": (filename, content, "text/plain")}
    data = {}
    if replaces_file_id is not None:
        data["replaces_file_id"] = str(replaces_file_id)
    resp = admin_client.post("/files/upload", files=files, data=data)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_upload_new_version_supersedes_old_one(admin_client):
    original = _upload_file(admin_client, filename="contract.txt", content=b"v1")
    assert original["version"] == 1

    new_version = _upload_file(
        admin_client, filename="contract.txt", content=b"v2", replaces_file_id=original["id"]
    )
    assert new_version["version"] == 2
    assert new_version["previous_version_id"] == original["id"]

    # The old version is hidden from the normal listing now
    listed = admin_client.get("/files/").json()
    assert all(f["id"] != original["id"] for f in listed)
    assert any(f["id"] == new_version["id"] for f in listed)

    # But the full history is still retrievable
    history = admin_client.get(f"/files/{new_version['id']}/versions").json()
    assert [h["id"] for h in history] == [new_version["id"], original["id"]]


def test_bulk_delete_files(admin_client):
    f1 = _upload_file(admin_client, filename="a.txt")
    f2 = _upload_file(admin_client, filename="b.txt")

    resp = admin_client.post("/files/bulk/delete", json={"file_ids": [f1["id"], f2["id"]]})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2

    listed = admin_client.get("/files/").json()
    assert all(f["id"] not in (f1["id"], f2["id"]) for f in listed)


def test_bulk_download_files_returns_zip(admin_client):
    f1 = _upload_file(admin_client, filename="x.txt", content=b"one")
    f2 = _upload_file(admin_client, filename="y.txt", content=b"two")

    resp = admin_client.post("/files/bulk/download", json={"file_ids": [f1["id"], f2["id"]]})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert resp.content[:2] == b"PK"  # zip file magic bytes
