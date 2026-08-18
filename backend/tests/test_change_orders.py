from tests.test_contracts import _create_contract
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _create_change_order(admin_client, contract_id, **overrides):
    payload = {
        "contract_id": contract_id,
        "title": "Additional fieldwork scope",
        "change_type": "fee_increase",
        "amount_delta": "5000.00",
    }
    payload.update(overrides)
    resp = admin_client.post("/change-orders/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _setup(admin_client, email):
    client = _create_client(admin_client, email=email)
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], value="50000.00")
    return client, project, contract


def test_create_change_order_defaults_to_pending(admin_client):
    _, project, contract = _setup(admin_client, "co-create@example.com")
    change_order = _create_change_order(admin_client, contract["id"])

    assert change_order["status"] == "pending"
    assert change_order["project_id"] == project["id"]
    assert change_order["contract_id"] == contract["id"]


def test_change_order_rejects_unknown_contract(admin_client):
    resp = admin_client.post(
        "/change-orders/",
        json={"contract_id": 999999, "title": "Ghost change", "change_type": "scope_change"},
    )
    assert resp.status_code == 404


def test_change_order_rejects_invalid_change_type(admin_client):
    _, _, contract = _setup(admin_client, "co-badtype@example.com")
    resp = admin_client.post(
        "/change-orders/", json={"contract_id": contract["id"], "title": "Bad", "change_type": "not_a_type"}
    )
    assert resp.status_code == 400


def test_change_order_rejects_wrong_sign_for_fee_increase(admin_client):
    _, _, contract = _setup(admin_client, "co-wrongsign@example.com")
    resp = admin_client.post(
        "/change-orders/",
        json={
            "contract_id": contract["id"],
            "title": "Bad sign",
            "change_type": "fee_increase",
            "amount_delta": "-100.00",
        },
    )
    assert resp.status_code == 400


def test_approve_change_order_applies_delta_to_contract_value(admin_client):
    _, _, contract = _setup(admin_client, "co-approve@example.com")
    change_order = _create_change_order(admin_client, contract["id"], amount_delta="5000.00")

    resp = admin_client.post(f"/change-orders/{change_order['id']}/approve")
    assert resp.status_code == 200, resp.text
    approved = resp.json()
    assert approved["status"] == "approved"
    assert approved["decided_by_email"]

    resp = admin_client.get(f"/contracts/{contract['id']}")
    assert resp.json()["value"] == "55000.00"


def test_reject_change_order_leaves_contract_value_unchanged(admin_client):
    _, _, contract = _setup(admin_client, "co-reject@example.com")
    change_order = _create_change_order(admin_client, contract["id"], amount_delta="5000.00")

    resp = admin_client.post(f"/change-orders/{change_order['id']}/reject", json={"reason": "Client declined"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    resp = admin_client.get(f"/contracts/{contract['id']}")
    assert resp.json()["value"] == "50000.00"


def test_cannot_approve_already_decided_change_order(admin_client):
    _, _, contract = _setup(admin_client, "co-double@example.com")
    change_order = _create_change_order(admin_client, contract["id"])
    admin_client.post(f"/change-orders/{change_order['id']}/approve")

    resp = admin_client.post(f"/change-orders/{change_order['id']}/approve")
    assert resp.status_code == 400


def test_cannot_edit_decided_change_order(admin_client):
    _, _, contract = _setup(admin_client, "co-editlock@example.com")
    change_order = _create_change_order(admin_client, contract["id"])
    admin_client.post(f"/change-orders/{change_order['id']}/approve")

    resp = admin_client.put(f"/change-orders/{change_order['id']}", json={"title": "New title"})
    assert resp.status_code == 400


def test_list_change_orders_filters_by_project(admin_client):
    _, project_a, contract_a = _setup(admin_client, "co-filter-a@example.com")
    _create_change_order(admin_client, contract_a["id"], title="A change")

    resp = admin_client.get(f"/change-orders/?project_id={project_a['id']}")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "A change"


def test_delete_change_order(admin_client):
    _, _, contract = _setup(admin_client, "co-delete@example.com")
    change_order = _create_change_order(admin_client, contract["id"])

    resp = admin_client.delete(f"/change-orders/{change_order['id']}")
    assert resp.status_code == 200

    resp = admin_client.get(f"/change-orders/{change_order['id']}")
    assert resp.status_code == 404
