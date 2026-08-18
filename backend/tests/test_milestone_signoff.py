from tests.conftest import ADMIN_EMAIL
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _create_milestone(admin_client, project_id, **overrides):
    payload = {"project_id": project_id, "name": "Audit findings draft"}
    payload.update(overrides)
    resp = admin_client.post("/milestones/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_milestone_defaults_to_no_signoff_tracked(admin_client):
    client = _create_client(admin_client, email="signoff-default@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    assert milestone["approval_status"] is None
    assert milestone["approved_at"] is None


def test_approve_milestone_signoff(admin_client):
    client = _create_client(admin_client, email="signoff-approve@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    resp = admin_client.put(f"/milestones/{milestone['id']}/signoff", json={"status": "approved"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["approval_status"] == "approved"
    assert body["approved_at"] is not None
    assert body["approved_by_email"] == ADMIN_EMAIL


def test_reject_milestone_signoff_with_reason(admin_client):
    client = _create_client(admin_client, email="signoff-reject@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    resp = admin_client.put(
        f"/milestones/{milestone['id']}/signoff",
        json={"status": "rejected", "reason": "Findings need more detail"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["approval_status"] == "rejected"
    assert body["approved_at"] is None
    assert body["rejection_reason"] == "Findings need more detail"


def test_signoff_rejects_invalid_status(admin_client):
    client = _create_client(admin_client, email="signoff-invalid@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    resp = admin_client.put(f"/milestones/{milestone['id']}/signoff", json={"status": "maybe"})
    assert resp.status_code == 400


def test_signoff_rejects_unknown_milestone(admin_client):
    resp = admin_client.put("/milestones/999999/signoff", json={"status": "approved"})
    assert resp.status_code == 404


def test_re_approving_after_reject_clears_rejection_reason(admin_client):
    client = _create_client(admin_client, email="signoff-reapprove@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    admin_client.put(f"/milestones/{milestone['id']}/signoff", json={"status": "rejected", "reason": "Needs work"})
    resp = admin_client.put(f"/milestones/{milestone['id']}/signoff", json={"status": "approved"})
    body = resp.json()
    assert body["approval_status"] == "approved"
    assert body["rejection_reason"] is None
