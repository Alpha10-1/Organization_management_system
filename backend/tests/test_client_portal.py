from tests.test_client_portal_auth import _activate_portal_user, _invite_portal_user
from tests.test_milestone_signoff import _create_milestone
from tests.test_new_features import _create_client
from tests.test_pbc_requests import _create_pbc_request
from tests.test_projects import _create_project


def _portal_client(admin_client, client, client_email, portal_email, password="ClientPass123!"):
    """Full setup: create a client, invite + activate a portal user for
    them, and return (org_client, portal test client) ready to hit
    /portal/* routes."""
    org_client = _create_client(admin_client, email=client_email)
    _invite_portal_user(admin_client, org_client["id"], email=portal_email)
    _activate_portal_user(client, portal_email, password=password)
    login = client.post("/portal/auth/login", data={"username": portal_email, "password": password})
    assert login.status_code == 200, login.text
    return org_client


# --- Engagements -------------------------------------------------------


def test_portal_user_sees_only_their_own_engagements(admin_client, client, staff_client):
    org_client = _portal_client(admin_client, client, "portal-eng-a@example.com", "eng-a@clientco.example.com")
    project_a = _create_project(admin_client, org_client["id"], name="A's Audit")

    other_client = _create_client(admin_client, email="portal-eng-b@example.com")
    _create_project(admin_client, other_client["id"], name="B's Audit")

    resp = client.get("/portal/engagements")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert names == {"A's Audit"}
    assert project_a["id"] in {p["id"] for p in resp.json()}


def test_portal_user_cannot_fetch_another_clients_engagement(admin_client, client):
    _portal_client(admin_client, client, "portal-eng-c@example.com", "eng-c@clientco.example.com")

    other_client = _create_client(admin_client, email="portal-eng-d@example.com")
    other_project = _create_project(admin_client, other_client["id"])

    resp = client.get(f"/portal/engagements/{other_project['id']}")
    assert resp.status_code == 404


def test_portal_engagement_view_omits_internal_fields(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-eng-e@example.com", "eng-e@clientco.example.com")
    project = _create_project(admin_client, org_client["id"], billing_notes="internal margin notes")

    resp = client.get(f"/portal/engagements/{project['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert "billing_notes" not in body
    assert "close_out_notes" not in body
    assert "risk_level" not in body


def test_unauthenticated_request_to_portal_engagements_401s(client):
    resp = client.get("/portal/engagements")
    assert resp.status_code == 401


# --- Milestones / client sign-off ---------------------------------------


def test_client_can_view_and_signoff_milestone(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-mile-a@example.com", "mile-a@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    listing = client.get(f"/portal/engagements/{project['id']}/milestones")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    resp = client.put(
        f"/portal/engagements/{project['id']}/milestones/{milestone['id']}/signoff",
        json={"status": "approved"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["approval_status"] == "approved"
    assert body["approved_by_email"] == "mile-a@clientco.example.com"
    assert body["approved_by_name"] == "Jamie CFO"


def test_client_milestone_rejection_records_reason(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-mile-b@example.com", "mile-b@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    milestone = _create_milestone(admin_client, project["id"])

    resp = client.put(
        f"/portal/engagements/{project['id']}/milestones/{milestone['id']}/signoff",
        json={"status": "rejected", "reason": "Numbers don't tie out"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["approval_status"] == "rejected"
    assert body["rejection_reason"] == "Numbers don't tie out"


def test_client_cannot_signoff_milestone_on_another_clients_engagement(admin_client, client):
    _portal_client(admin_client, client, "portal-mile-c@example.com", "mile-c@clientco.example.com")

    other_client = _create_client(admin_client, email="portal-mile-d@example.com")
    other_project = _create_project(admin_client, other_client["id"])
    other_milestone = _create_milestone(admin_client, other_project["id"])

    resp = client.put(
        f"/portal/engagements/{other_project['id']}/milestones/{other_milestone['id']}/signoff",
        json={"status": "approved"},
    )
    assert resp.status_code == 404


# --- PBC requests / upload -----------------------------------------------


def test_client_sees_pbc_requests_for_their_engagement(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-pbc-a@example.com", "pbc-a@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    _create_pbc_request(admin_client, project["id"], title="Bank confirmations")

    resp = client.get(f"/portal/engagements/{project['id']}/pbc-requests")
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Bank confirmations"
    assert resp.json()[0]["status"] == "requested"


def test_client_can_upload_document_against_pbc_request(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-pbc-b@example.com", "pbc-b@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    pbc = _create_pbc_request(admin_client, project["id"], title="Trial balance")

    resp = client.post(
        f"/portal/pbc-requests/{pbc['id']}/upload",
        files={"file": ("trial_balance.xlsx", b"fake spreadsheet bytes", "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "submitted"
    assert body["submitted_by_email"] == "pbc-b@clientco.example.com"
    assert body["file_id"] is not None

    # And staff sees it as submitted, ready for review.
    staff_view = admin_client.get(f"/pbc-requests/{pbc['id']}")
    assert staff_view.json()["status"] == "submitted"


def test_client_upload_rejects_disallowed_extension(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-pbc-c@example.com", "pbc-c@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    pbc = _create_pbc_request(admin_client, project["id"], title="Malware maybe")

    resp = client.post(
        f"/portal/pbc-requests/{pbc['id']}/upload",
        files={"file": ("evil.exe", b"MZ\x00\x00", "application/octet-stream")},
    )
    assert resp.status_code == 415


def test_client_cannot_upload_against_another_clients_pbc_request(admin_client, client):
    _portal_client(admin_client, client, "portal-pbc-d@example.com", "pbc-d@clientco.example.com")

    other_client = _create_client(admin_client, email="portal-pbc-e@example.com")
    other_project = _create_project(admin_client, other_client["id"])
    other_pbc = _create_pbc_request(admin_client, other_project["id"], title="Not yours")

    resp = client.post(
        f"/portal/pbc-requests/{other_pbc['id']}/upload",
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 404


def test_staff_review_approve_locks_status(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-pbc-f@example.com", "pbc-f@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    pbc = _create_pbc_request(admin_client, project["id"], title="Payroll register")

    client.post(
        f"/portal/pbc-requests/{pbc['id']}/upload",
        files={"file": ("payroll.csv", b"name,amount\nJane,100", "text/csv")},
    )

    review = admin_client.put(f"/pbc-requests/{pbc['id']}/review", json={"status": "approved"})
    assert review.status_code == 200
    assert review.json()["status"] == "approved"

    # Approved requests aren't re-reviewable.
    second_review = admin_client.put(f"/pbc-requests/{pbc['id']}/review", json={"status": "approved"})
    assert second_review.status_code == 400


def test_staff_rejection_reopens_request_for_resubmission(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-pbc-g@example.com", "pbc-g@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])
    pbc = _create_pbc_request(admin_client, project["id"], title="Lease schedule")

    client.post(
        f"/portal/pbc-requests/{pbc['id']}/upload",
        files={"file": ("lease.pdf", b"%PDF-1.4 old version", "application/pdf")},
    )

    review = admin_client.put(
        f"/pbc-requests/{pbc['id']}/review", json={"status": "rejected", "notes": "Wrong fiscal year"}
    )
    assert review.status_code == 200
    assert review.json()["status"] == "requested"
    assert review.json()["review_notes"] == "Wrong fiscal year"

    # Client can now see it back in their outstanding list and resubmit.
    outstanding = client.get(f"/portal/engagements/{project['id']}/pbc-requests", params={"status": "requested"})
    assert any(p["id"] == pbc["id"] for p in outstanding.json())

    resubmit = client.post(
        f"/portal/pbc-requests/{pbc['id']}/upload",
        files={"file": ("lease_v2.pdf", b"%PDF-1.4 new version", "application/pdf")},
    )
    assert resubmit.status_code == 200
    assert resubmit.json()["status"] == "submitted"
    assert resubmit.json()["review_notes"] is None


# --- Shared files ----------------------------------------------------------


def test_client_can_view_files_shared_on_their_engagement(admin_client, client):
    org_client = _portal_client(admin_client, client, "portal-files-a@example.com", "files-a@clientco.example.com")
    project = _create_project(admin_client, org_client["id"])

    admin_client.post(
        "/files/upload",
        files={"file": ("deliverable.pdf", b"%PDF-1.4 report", "application/pdf")},
        data={"project_id": str(project["id"])},
    )

    resp = client.get(f"/portal/engagements/{project['id']}/files")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["original_name"] == "deliverable.pdf"
    assert "stored_name" not in resp.json()[0]
    assert "file_path" not in resp.json()[0]
