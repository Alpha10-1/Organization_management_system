from app.core.config import settings
from tests.test_change_orders import _create_change_order
from tests.test_contracts import _create_contract
from tests.test_new_features import _create_client
from tests.test_projects import _create_project

WEBHOOK_HEADERS = {"X-Esign-Webhook-Secret": settings.ESIGN_WEBHOOK_SECRET}


def _setup_draft_contract(admin_client, email):
    client = _create_client(admin_client, email=email)
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="draft")
    return client, project, contract


# --- Contracts ---------------------------------------------------------


def test_send_contract_for_signature_creates_envelope_and_marks_sent(admin_client):
    _, _, contract = _setup_draft_contract(admin_client, "esign-contract-a@example.com")

    resp = admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    assert resp.status_code == 200, resp.text
    envelope = resp.json()
    assert envelope["document_type"] == "contract"
    assert envelope["document_id"] == contract["id"]
    assert envelope["status"] == "sent"
    assert envelope["provider"] == "mock"
    assert envelope["provider_envelope_id"].startswith("mock-")

    updated_contract = admin_client.get(f"/contracts/{contract['id']}").json()
    assert updated_contract["status"] == "sent"


def test_cannot_send_signed_contract_for_signature(admin_client):
    client = _create_client(admin_client, email="esign-contract-b@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="signed")

    resp = admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    assert resp.status_code == 400


def test_list_contract_signature_envelopes(admin_client):
    _, _, contract = _setup_draft_contract(admin_client, "esign-contract-c@example.com")

    admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )

    resp = admin_client.get(f"/contracts/{contract['id']}/signature-envelopes")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["signer_email"] == "cfo@clientco.example.com"


# --- Webhook: contracts --------------------------------------------------


def test_webhook_completes_envelope_and_marks_contract_signed(admin_client):
    _, _, contract = _setup_draft_contract(admin_client, "esign-webhook-a@example.com")
    send = admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    envelope_id = send.json()["provider_envelope_id"]

    resp = admin_client.post(
        "/esign/webhook",
        json={"provider_envelope_id": envelope_id, "status": "completed"},
        headers=WEBHOOK_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None

    updated_contract = admin_client.get(f"/contracts/{contract['id']}").json()
    assert updated_contract["status"] == "signed"
    assert updated_contract["signed_date"] is not None


def test_webhook_declined_does_not_mark_contract_signed(admin_client):
    _, _, contract = _setup_draft_contract(admin_client, "esign-webhook-b@example.com")
    send = admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    envelope_id = send.json()["provider_envelope_id"]

    resp = admin_client.post(
        "/esign/webhook",
        json={"provider_envelope_id": envelope_id, "status": "declined", "reason": "Wrong fee schedule"},
        headers=WEBHOOK_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "declined"
    assert resp.json()["decline_reason"] == "Wrong fee schedule"

    updated_contract = admin_client.get(f"/contracts/{contract['id']}").json()
    assert updated_contract["status"] == "sent"  # unchanged, not "signed"


def test_webhook_rejects_wrong_secret(admin_client):
    _, _, contract = _setup_draft_contract(admin_client, "esign-webhook-c@example.com")
    send = admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    envelope_id = send.json()["provider_envelope_id"]

    resp = admin_client.post(
        "/esign/webhook",
        json={"provider_envelope_id": envelope_id, "status": "completed"},
        headers={"X-Esign-Webhook-Secret": "wrong-secret"},
    )
    assert resp.status_code == 401

    # And with no header at all.
    resp2 = admin_client.post("/esign/webhook", json={"provider_envelope_id": envelope_id, "status": "completed"})
    assert resp2.status_code == 401


def test_webhook_unknown_envelope_404s(admin_client):
    resp = admin_client.post(
        "/esign/webhook",
        json={"provider_envelope_id": "mock-does-not-exist", "status": "completed"},
        headers=WEBHOOK_HEADERS,
    )
    assert resp.status_code == 404


def test_webhook_cannot_replay_on_already_terminal_envelope(admin_client):
    _, _, contract = _setup_draft_contract(admin_client, "esign-webhook-d@example.com")
    send = admin_client.post(
        f"/contracts/{contract['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    envelope_id = send.json()["provider_envelope_id"]

    first = admin_client.post(
        "/esign/webhook", json={"provider_envelope_id": envelope_id, "status": "completed"}, headers=WEBHOOK_HEADERS
    )
    assert first.status_code == 200

    second = admin_client.post(
        "/esign/webhook", json={"provider_envelope_id": envelope_id, "status": "completed"}, headers=WEBHOOK_HEADERS
    )
    assert second.status_code == 400


# --- Change orders -------------------------------------------------------


def test_send_change_order_for_signature_requires_approval(admin_client):
    client = _create_client(admin_client, email="esign-co-a@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="signed")
    change_order = _create_change_order(admin_client, contract["id"])

    resp = admin_client.post(
        f"/change-orders/{change_order['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    assert resp.status_code == 400  # still pending, not approved


def test_send_approved_change_order_for_signature(admin_client):
    client = _create_client(admin_client, email="esign-co-b@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="signed", value="50000.00")
    change_order = _create_change_order(admin_client, contract["id"])

    admin_client.post(f"/change-orders/{change_order['id']}/approve")

    resp = admin_client.post(
        f"/change-orders/{change_order['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    assert resp.status_code == 200, resp.text
    envelope = resp.json()
    assert envelope["document_type"] == "change_order"
    assert envelope["document_id"] == change_order["id"]

    updated_co = admin_client.get(f"/change-orders/{change_order['id']}").json()
    assert updated_co["signature_status"] == "sent"
    # The internal approval already applied the delta -- sending for
    # signature is a separate concern and shouldn't touch it again.
    assert updated_co["status"] == "approved"


def test_webhook_completes_change_order_signature(admin_client):
    client = _create_client(admin_client, email="esign-co-c@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="signed", value="50000.00")
    change_order = _create_change_order(admin_client, contract["id"])
    admin_client.post(f"/change-orders/{change_order['id']}/approve")

    send = admin_client.post(
        f"/change-orders/{change_order['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    envelope_id = send.json()["provider_envelope_id"]

    resp = admin_client.post(
        "/esign/webhook", json={"provider_envelope_id": envelope_id, "status": "completed"}, headers=WEBHOOK_HEADERS
    )
    assert resp.status_code == 200

    updated_co = admin_client.get(f"/change-orders/{change_order['id']}").json()
    assert updated_co["signature_status"] == "completed"
    assert updated_co["signed_at"] is not None


def test_cannot_send_change_order_for_signature_twice_while_outstanding(admin_client):
    client = _create_client(admin_client, email="esign-co-d@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="signed", value="50000.00")
    change_order = _create_change_order(admin_client, contract["id"])
    admin_client.post(f"/change-orders/{change_order['id']}/approve")

    first = admin_client.post(
        f"/change-orders/{change_order['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    assert first.status_code == 200

    second = admin_client.post(
        f"/change-orders/{change_order['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )
    assert second.status_code == 400


def test_list_change_order_signature_envelopes(admin_client):
    client = _create_client(admin_client, email="esign-co-e@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], status="signed", value="50000.00")
    change_order = _create_change_order(admin_client, contract["id"])
    admin_client.post(f"/change-orders/{change_order['id']}/approve")

    admin_client.post(
        f"/change-orders/{change_order['id']}/send-for-signature",
        json={"signer_email": "cfo@clientco.example.com", "signer_name": "Pat CFO"},
    )

    resp = admin_client.get(f"/change-orders/{change_order['id']}/signature-envelopes")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
