import uuid

from tests.test_staffing import _create_user

PROSPECTS_URL = "/prospects"
PROPOSALS_URL = "/proposals"


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_prospect(admin_client, **overrides):
    payload = {
        "name": _unique_name("Acme Prospect"),
        "company_name": "Acme Co",
        "contact_email": "biz@acme.example.com",
        "source": "referral",
    }
    payload.update(overrides)
    resp = admin_client.post(f"{PROSPECTS_URL}/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_proposal(admin_client, prospect_id, **overrides):
    payload = {
        "prospect_id": prospect_id,
        "title": "Initial audit engagement proposal",
        "proposed_value": "50000.00",
    }
    payload.update(overrides)
    resp = admin_client.post(f"{PROPOSALS_URL}/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _advance(admin_client, prospect_id, status, notes=None):
    body = {"status": status}
    if notes is not None:
        body["notes"] = notes
    return admin_client.patch(f"{PROSPECTS_URL}/{prospect_id}/status", json=body)


# --- basic CRUD --------------------------------------------------------------


def test_create_prospect_defaults_to_new_status(admin_client):
    prospect = _create_prospect(admin_client)
    assert prospect["status"] == "new"
    assert prospect["source"] == "referral"


def test_create_prospect_rejects_invalid_source(admin_client):
    resp = admin_client.post(
        f"{PROSPECTS_URL}/",
        json={"name": "Bad Source Co", "source": "carrier_pigeon"},
    )
    assert resp.status_code == 400


def test_update_prospect_fields(admin_client):
    prospect = _create_prospect(admin_client)
    resp = admin_client.put(f"{PROSPECTS_URL}/{prospect['id']}", json={"industry": "Manufacturing"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["industry"] == "Manufacturing"


def test_get_unknown_prospect_404(admin_client):
    resp = admin_client.get(f"{PROSPECTS_URL}/999999")
    assert resp.status_code == 404


def test_delete_prospect_soft_deletes(admin_client):
    prospect = _create_prospect(admin_client)
    resp = admin_client.delete(f"{PROSPECTS_URL}/{prospect['id']}")
    assert resp.status_code == 200
    resp = admin_client.get(f"{PROSPECTS_URL}/{prospect['id']}")
    assert resp.status_code == 404


def test_prospect_assigned_to_resolves_name_and_email(admin_client):
    owner = _create_user(admin_client, email=f"{_unique_name('bd-owner')}@example.com")
    prospect = _create_prospect(admin_client, assigned_to_user_id=owner["id"])
    assert prospect["assigned_to_email"] == owner["email"]
    assert prospect["assigned_to_name"] == owner["name"]


def test_prospect_requires_auth(client):
    resp = client.get(f"{PROSPECTS_URL}/")
    assert resp.status_code == 401


# --- stage transitions ---------------------------------------------------------


def test_prospect_valid_forward_transition(admin_client):
    prospect = _create_prospect(admin_client)
    resp = _advance(admin_client, prospect["id"], "contacted")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "contacted"


def test_prospect_rejects_skipping_stages(admin_client):
    prospect = _create_prospect(admin_client)
    resp = _advance(admin_client, prospect["id"], "negotiating")
    assert resp.status_code == 400


def test_prospect_rejects_invalid_status_value(admin_client):
    prospect = _create_prospect(admin_client)
    resp = _advance(admin_client, prospect["id"], "vibing")
    assert resp.status_code == 400


def test_prospect_lost_requires_reason(admin_client):
    prospect = _create_prospect(admin_client)
    resp = _advance(admin_client, prospect["id"], "lost")
    assert resp.status_code == 400


def test_prospect_lost_with_reason_succeeds_and_sets_lost_reason(admin_client):
    prospect = _create_prospect(admin_client)
    resp = _advance(admin_client, prospect["id"], "lost", notes="Went with a competitor")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "lost"
    assert body["lost_reason"] == "Went with a competitor"


def test_terminal_status_cannot_transition_further(admin_client):
    prospect = _create_prospect(admin_client)
    _advance(admin_client, prospect["id"], "lost", notes="No budget")
    resp = _advance(admin_client, prospect["id"], "contacted")
    assert resp.status_code == 400


def test_prospect_stage_history_records_transitions(admin_client):
    prospect = _create_prospect(admin_client)
    _advance(admin_client, prospect["id"], "contacted")
    _advance(admin_client, prospect["id"], "qualified")

    resp = admin_client.get(f"{PROSPECTS_URL}/{prospect['id']}/stage-history")
    assert resp.status_code == 200, resp.text
    events = resp.json()
    assert len(events) == 2
    assert events[0]["from_status"] == "new"
    assert events[0]["to_status"] == "contacted"
    assert events[1]["to_status"] == "qualified"


def test_prospect_won_requires_accepted_proposal(admin_client):
    prospect = _create_prospect(admin_client)
    _advance(admin_client, prospect["id"], "contacted")
    _advance(admin_client, prospect["id"], "qualified")
    _advance(admin_client, prospect["id"], "proposal_sent")

    resp = _advance(admin_client, prospect["id"], "won")
    assert resp.status_code == 400


def test_prospect_won_succeeds_with_accepted_proposal(admin_client):
    prospect = _create_prospect(admin_client)
    _advance(admin_client, prospect["id"], "contacted")
    _advance(admin_client, prospect["id"], "qualified")
    _advance(admin_client, prospect["id"], "proposal_sent")

    proposal = _create_proposal(admin_client, prospect["id"])
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "sent"})
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "accepted"})

    resp = _advance(admin_client, prospect["id"], "won")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "won"


# --- proposals -------------------------------------------------------------


def test_create_proposal_defaults_to_draft(admin_client):
    prospect = _create_prospect(admin_client)
    proposal = _create_proposal(admin_client, prospect["id"])
    assert proposal["status"] == "draft"


def test_cannot_add_proposal_to_closed_prospect(admin_client):
    prospect = _create_prospect(admin_client)
    _advance(admin_client, prospect["id"], "lost", notes="No budget")
    resp = admin_client.post(
        f"{PROPOSALS_URL}/",
        json={"prospect_id": prospect["id"], "title": "Too late"},
    )
    assert resp.status_code == 400


def test_proposal_status_transition_sequence(admin_client):
    prospect = _create_prospect(admin_client)
    proposal = _create_proposal(admin_client, prospect["id"])

    resp = admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "sent"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["sent_date"] is not None

    resp = admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "accepted"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["decided_at"] is not None


def test_proposal_cannot_skip_to_accepted_from_draft(admin_client):
    prospect = _create_prospect(admin_client)
    proposal = _create_proposal(admin_client, prospect["id"])
    resp = admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "accepted"})
    assert resp.status_code == 400


def test_proposal_terminal_status_is_final(admin_client):
    prospect = _create_prospect(admin_client)
    proposal = _create_proposal(admin_client, prospect["id"])
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "sent"})
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "rejected"})

    resp = admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "sent"})
    assert resp.status_code == 400


def test_only_draft_proposal_editable_via_put(admin_client):
    prospect = _create_prospect(admin_client)
    proposal = _create_proposal(admin_client, prospect["id"])
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "sent"})

    resp = admin_client.put(f"{PROPOSALS_URL}/{proposal['id']}", json={"title": "Revised title"})
    assert resp.status_code == 400


def test_list_proposals_filters_by_prospect(admin_client):
    prospect_a = _create_prospect(admin_client)
    prospect_b = _create_prospect(admin_client)
    _create_proposal(admin_client, prospect_a["id"], title="For A")
    _create_proposal(admin_client, prospect_b["id"], title="For B")

    resp = admin_client.get(PROPOSALS_URL + "/", params={"prospect_id": prospect_a["id"]})
    assert resp.status_code == 200, resp.text
    titles = {p["title"] for p in resp.json()}
    assert titles == {"For A"}


# --- convert to client -------------------------------------------------------


def test_convert_requires_won_status(admin_client):
    prospect = _create_prospect(admin_client)
    resp = admin_client.post(f"{PROSPECTS_URL}/{prospect['id']}/convert", json={})
    assert resp.status_code == 400


def _win_prospect(admin_client, prospect):
    _advance(admin_client, prospect["id"], "contacted")
    _advance(admin_client, prospect["id"], "qualified")
    _advance(admin_client, prospect["id"], "proposal_sent")
    proposal = _create_proposal(admin_client, prospect["id"])
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "sent"})
    admin_client.patch(f"{PROPOSALS_URL}/{proposal['id']}/status", json={"status": "accepted"})
    resp = _advance(admin_client, prospect["id"], "won")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_convert_won_prospect_with_company_name_creates_business_client(admin_client):
    prospect = _create_prospect(admin_client, company_name="Widgets Inc")
    won = _win_prospect(admin_client, prospect)

    resp = admin_client.post(f"{PROSPECTS_URL}/{won['id']}/convert", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["converted_client_id"] is not None

    client_resp = admin_client.get(f"/clients/{body['converted_client_id']}")
    assert client_resp.status_code == 200
    client = client_resp.json()
    assert client["client_type"] == "business"
    assert client["company_name"] == "Widgets Inc"


def test_convert_won_prospect_without_company_name_creates_individual_client(admin_client):
    prospect = _create_prospect(admin_client, name="Jordan Smith", company_name=None)
    won = _win_prospect(admin_client, prospect)

    resp = admin_client.post(f"{PROSPECTS_URL}/{won['id']}/convert", json={})
    assert resp.status_code == 200, resp.text
    client = admin_client.get(f"/clients/{resp.json()['converted_client_id']}").json()
    assert client["client_type"] == "individual"
    assert client["first_name"] == "Jordan"
    assert client["last_name"] == "Smith"


def test_convert_twice_rejected(admin_client):
    prospect = _create_prospect(admin_client, company_name="OnceOnly Inc")
    won = _win_prospect(admin_client, prospect)
    resp1 = admin_client.post(f"{PROSPECTS_URL}/{won['id']}/convert", json={})
    assert resp1.status_code == 200

    resp2 = admin_client.post(f"{PROSPECTS_URL}/{won['id']}/convert", json={})
    assert resp2.status_code == 400


# --- pipeline summary -------------------------------------------------------


def test_pipeline_summary_reports_stage_counts_and_win_rate(admin_client):
    won_prospect = _create_prospect(admin_client, company_name="WinCo")
    _win_prospect(admin_client, won_prospect)

    lost_prospect = _create_prospect(admin_client)
    _advance(admin_client, lost_prospect["id"], "lost", notes="No fit")

    open_prospect = _create_prospect(admin_client, estimated_value="12000.00")

    resp = admin_client.get(f"{PROSPECTS_URL}/pipeline-summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["won_count"] >= 1
    assert body["lost_count"] >= 1
    assert body["win_rate_percent"] is not None
    stage_counts = {s["status"]: s["count"] for s in body["stages"]}
    assert stage_counts["won"] >= 1
    assert stage_counts["lost"] >= 1
    assert float(body["open_pipeline_value"]) >= 12000.00
