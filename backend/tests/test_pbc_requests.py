from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _create_pbc_request(admin_client, project_id, **overrides):
    payload = {"project_id": project_id, "title": "Q4 Trial Balance"}
    payload.update(overrides)
    resp = admin_client.post("/pbc-requests/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _setup_project(admin_client, email="pbc-project@example.com"):
    client = _create_client(admin_client, email=email)
    project = _create_project(admin_client, client["id"])
    return client, project


def test_create_pbc_request(admin_client):
    _, project = _setup_project(admin_client)
    pbc = _create_pbc_request(admin_client, project["id"], category="Financial Statements")

    assert pbc["project_id"] == project["id"]
    assert pbc["status"] == "requested"
    assert pbc["category"] == "Financial Statements"
    assert pbc["file_id"] is None


def test_list_pbc_requests_by_project(admin_client):
    _, project_a = _setup_project(admin_client, email="pbc-list-a@example.com")
    _, project_b = _setup_project(admin_client, email="pbc-list-b@example.com")
    _create_pbc_request(admin_client, project_a["id"], title="A1")
    _create_pbc_request(admin_client, project_a["id"], title="A2")
    _create_pbc_request(admin_client, project_b["id"], title="B1")

    resp = admin_client.get("/pbc-requests/", params={"project_id": project_a["id"]})
    assert resp.status_code == 200
    titles = {p["title"] for p in resp.json()}
    assert titles == {"A1", "A2"}


def test_update_pbc_request(admin_client):
    _, project = _setup_project(admin_client, email="pbc-update@example.com")
    pbc = _create_pbc_request(admin_client, project["id"])

    resp = admin_client.put(f"/pbc-requests/{pbc['id']}", json={"title": "Updated title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated title"


def test_delete_pbc_request_soft_deletes(admin_client):
    _, project = _setup_project(admin_client, email="pbc-delete@example.com")
    pbc = _create_pbc_request(admin_client, project["id"])

    resp = admin_client.delete(f"/pbc-requests/{pbc['id']}")
    assert resp.status_code == 200

    listing = admin_client.get("/pbc-requests/", params={"project_id": project["id"]})
    assert listing.json() == []


def test_cannot_review_unsubmitted_pbc_request(admin_client):
    _, project = _setup_project(admin_client, email="pbc-review-early@example.com")
    pbc = _create_pbc_request(admin_client, project["id"])

    resp = admin_client.put(f"/pbc-requests/{pbc['id']}/review", json={"status": "approved"})
    assert resp.status_code == 400


def test_review_rejects_invalid_status(admin_client):
    _, project = _setup_project(admin_client, email="pbc-review-invalid@example.com")
    pbc = _create_pbc_request(admin_client, project["id"])

    resp = admin_client.put(f"/pbc-requests/{pbc['id']}/review", json={"status": "not-a-real-status"})
    assert resp.status_code in (400, 422)


def test_create_pbc_request_for_unknown_project_404s(admin_client):
    resp = admin_client.post("/pbc-requests/", json={"project_id": 999999, "title": "Ghost"})
    assert resp.status_code == 404
