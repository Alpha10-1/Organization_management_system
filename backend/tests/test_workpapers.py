import uuid

from tests.conftest import ADMIN_EMAIL
from tests.test_independence import _create_user, _unique_email
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _setup_project(admin_client):
    client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, client["id"])
    return project


def _create_workpaper(admin_client, project_id, **overrides):
    payload = {
        "project_id": project_id,
        "name": "Cash reconciliation",
        "description": "Reconcile bank statements to GL.",
        "category": "fieldwork",
    }
    payload.update(overrides)
    resp = admin_client.post("/workpapers/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Create / read -----------------------------------------------------------


def test_create_workpaper_defaults_to_self_as_preparer(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    assert workpaper["stage"] == "in_preparation"
    assert workpaper["prepared_by_email"] == ADMIN_EMAIL
    assert workpaper["reviewer_id"] is None
    assert workpaper["partner_id"] is None


def test_create_workpaper_with_explicit_preparer_reviewer_partner(admin_client):
    project = _setup_project(admin_client)
    preparer = _create_user(admin_client)
    reviewer = _create_user(admin_client)
    partner = _create_user(admin_client, role="admin")

    workpaper = _create_workpaper(
        admin_client,
        project["id"],
        preparer_id=preparer["id"],
        reviewer_id=reviewer["id"],
        partner_id=partner["id"],
    )
    assert workpaper["preparer_id"] == preparer["id"]
    assert workpaper["reviewer_id"] == reviewer["id"]
    assert workpaper["partner_id"] == partner["id"]
    assert workpaper["prepared_by_email"] == preparer["email"]


def test_create_workpaper_requires_valid_project(admin_client):
    resp = admin_client.post(
        "/workpapers/", json={"project_id": 999999, "name": "Orphan workpaper"}
    )
    assert resp.status_code == 404


def test_list_workpapers_filters_by_stage_and_project(admin_client):
    project = _setup_project(admin_client)
    other_project = _setup_project(admin_client)
    _create_workpaper(admin_client, project["id"], name="WP A")
    _create_workpaper(admin_client, other_project["id"], name="WP B")

    resp = admin_client.get("/workpapers/", params={"project_id": project["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "WP A"

    resp = admin_client.get("/workpapers/", params={"stage": "in_preparation"})
    assert resp.status_code == 200
    assert all(w["stage"] == "in_preparation" for w in resp.json())


def test_get_events_starts_empty(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.get(f"/workpapers/{workpaper['id']}/events")
    assert resp.status_code == 200
    assert resp.json() == []


# --- Update --------------------------------------------------------------


def test_update_workpaper_fields(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.put(f"/workpapers/{workpaper['id']}", json={"description": "Updated scope."})
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] == "Updated scope."


def test_update_rejects_unknown_reviewer(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.put(f"/workpapers/{workpaper['id']}", json={"reviewer_id": 999999})
    assert resp.status_code == 404


# --- Submit for review ----------------------------------------------------


def test_submit_requires_reviewer_assigned(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})
    assert resp.status_code == 400


def test_submit_moves_to_pending_review_and_logs_event(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.put(
        f"/workpapers/{workpaper['id']}/submit", json={"reviewer_id": reviewer["id"], "notes": "Ready for review."}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "pending_review"
    assert body["reviewer_id"] == reviewer["id"]
    assert body["submitted_for_review_at"] is not None

    events = admin_client.get(f"/workpapers/{workpaper['id']}/events").json()
    assert [e["event_type"] for e in events] == ["submitted_for_review"]


def test_submit_wrong_stage_rejected(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"], reviewer_id=reviewer["id"])
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})

    # Already pending_review -- submitting again should fail.
    resp = admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})
    assert resp.status_code == 400


# --- Review decision -------------------------------------------------------


def test_review_wrong_stage_rejected(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})
    assert resp.status_code == 400


def test_review_approve_requires_partner_assigned(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"], reviewer_id=reviewer["id"])
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})

    resp = admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})
    assert resp.status_code == 400
    assert "partner" in resp.json()["detail"].lower()


def test_review_approve_moves_to_partner_signoff(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    partner = _create_user(admin_client, role="admin")
    workpaper = _create_workpaper(
        admin_client, project["id"], reviewer_id=reviewer["id"], partner_id=partner["id"]
    )
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})

    resp = admin_client.put(
        f"/workpapers/{workpaper['id']}/review", json={"status": "approved", "notes": "Looks good."}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "pending_partner_signoff"
    assert body["review_status"] == "approved"

    events = admin_client.get(f"/workpapers/{workpaper['id']}/events").json()
    assert [e["event_type"] for e in events] == ["submitted_for_review", "review_approved"]


def test_review_reject_sends_back_to_preparation(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"], reviewer_id=reviewer["id"])
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})

    resp = admin_client.put(
        f"/workpapers/{workpaper['id']}/review", json={"status": "rejected", "notes": "Needs more testing."}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "in_preparation"
    assert body["review_status"] == "rejected"
    assert body["submitted_for_review_at"] is None

    events = admin_client.get(f"/workpapers/{workpaper['id']}/events").json()
    assert [e["event_type"] for e in events] == ["submitted_for_review", "review_rejected"]


def test_non_reviewer_staff_cannot_record_review(staff_client, admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"], reviewer_id=reviewer["id"])
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})

    resp = staff_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})
    assert resp.status_code == 403


# --- Partner sign-off -------------------------------------------------------


def test_partner_signoff_wrong_stage_rejected(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.put(f"/workpapers/{workpaper['id']}/partner-signoff", json={"status": "approved"})
    assert resp.status_code == 400


def test_full_chain_reaches_complete(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    partner = _create_user(admin_client, role="admin")
    workpaper = _create_workpaper(
        admin_client, project["id"], reviewer_id=reviewer["id"], partner_id=partner["id"]
    )

    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})
    admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})
    resp = admin_client.put(
        f"/workpapers/{workpaper['id']}/partner-signoff", json={"status": "approved", "notes": "Signed off."}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "complete"
    assert body["partner_status"] == "approved"
    assert body["partner_signed_off_at"] is not None

    events = admin_client.get(f"/workpapers/{workpaper['id']}/events").json()
    assert [e["event_type"] for e in events] == [
        "submitted_for_review",
        "review_approved",
        "partner_approved",
    ]


def test_partner_reject_sends_all_the_way_back_to_preparation(admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    partner = _create_user(admin_client, role="admin")
    workpaper = _create_workpaper(
        admin_client, project["id"], reviewer_id=reviewer["id"], partner_id=partner["id"]
    )

    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})
    admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})
    resp = admin_client.put(
        f"/workpapers/{workpaper['id']}/partner-signoff",
        json={"status": "rejected", "notes": "Sampling methodology unclear."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "in_preparation"
    assert body["partner_status"] == "rejected"
    assert body["review_status"] is None
    assert body["submitted_for_review_at"] is None

    events = admin_client.get(f"/workpapers/{workpaper['id']}/events").json()
    assert [e["event_type"] for e in events] == [
        "submitted_for_review",
        "review_approved",
        "partner_rejected",
    ]


def test_rework_and_resubmit_after_rejection_produces_full_history(admin_client):
    """A workpaper can be rejected and cycle through the chain again --
    the event log should show both rounds, not just the latest."""
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    partner = _create_user(admin_client, role="admin")
    workpaper = _create_workpaper(
        admin_client, project["id"], reviewer_id=reviewer["id"], partner_id=partner["id"]
    )

    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})
    admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "rejected", "notes": "Round 1 issues."})
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={"notes": "Fixed."})
    admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})
    resp = admin_client.put(f"/workpapers/{workpaper['id']}/partner-signoff", json={"status": "approved"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["stage"] == "complete"

    events = admin_client.get(f"/workpapers/{workpaper['id']}/events").json()
    assert [e["event_type"] for e in events] == [
        "submitted_for_review",
        "review_rejected",
        "submitted_for_review",
        "review_approved",
        "partner_approved",
    ]


def test_non_partner_staff_cannot_signoff(staff_client, admin_client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client)
    partner = _create_user(admin_client, role="admin")
    workpaper = _create_workpaper(
        admin_client, project["id"], reviewer_id=reviewer["id"], partner_id=partner["id"]
    )
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})
    admin_client.put(f"/workpapers/{workpaper['id']}/review", json={"status": "approved"})

    resp = staff_client.put(f"/workpapers/{workpaper['id']}/partner-signoff", json={"status": "approved"})
    assert resp.status_code == 403


# --- Delete ------------------------------------------------------------


def test_delete_workpaper_soft_deletes(admin_client):
    project = _setup_project(admin_client)
    workpaper = _create_workpaper(admin_client, project["id"])

    resp = admin_client.delete(f"/workpapers/{workpaper['id']}")
    assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/workpapers/{workpaper['id']}")
    assert resp.status_code == 404
