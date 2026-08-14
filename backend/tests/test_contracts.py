from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _create_contract(admin_client, project_id, **overrides):
    payload = {
        "project_id": project_id,
        "name": "FY26 Audit Engagement Letter",
        "billing_type": "fixed_fee",
        "value": "50000.00",
        "status": "signed",
    }
    payload.update(overrides)
    resp = admin_client.post("/contracts/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_and_get_contract(admin_client):
    client = _create_client(admin_client, email="contract-client@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"])

    assert contract["billing_type"] == "fixed_fee"
    assert contract["status"] == "signed"
    assert contract["created_by_email"]

    resp = admin_client.get(f"/contracts/{contract['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == contract["id"]


def test_contract_rejects_unknown_project(admin_client):
    resp = admin_client.post(
        "/contracts/", json={"project_id": 999999, "name": "Ghost SOW", "billing_type": "fixed_fee"}
    )
    assert resp.status_code == 404


def test_contract_rejects_invalid_billing_type(admin_client):
    client = _create_client(admin_client, email="bad-billing@example.com")
    project = _create_project(admin_client, client["id"])
    resp = admin_client.post(
        "/contracts/", json={"project_id": project["id"], "name": "Bad", "billing_type": "crypto"}
    )
    assert resp.status_code == 400


def test_contract_rejects_expiry_before_signed(admin_client):
    client = _create_client(admin_client, email="bad-dates@example.com")
    project = _create_project(admin_client, client["id"])
    resp = admin_client.post(
        "/contracts/",
        json={
            "project_id": project["id"],
            "name": "Backwards",
            "signed_date": "2026-06-01",
            "expiry_date": "2026-01-01",
        },
    )
    assert resp.status_code == 400


def test_list_contracts_filters_by_project(admin_client):
    client = _create_client(admin_client, email="filter-contracts@example.com")
    project_a = _create_project(admin_client, client["id"], name="Engagement A")
    project_b = _create_project(admin_client, client["id"], name="Engagement B")

    contract_a = _create_contract(admin_client, project_a["id"], name="Contract A")
    _create_contract(admin_client, project_b["id"], name="Contract B")

    resp = admin_client.get(f"/contracts/?project_id={project_a['id']}")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract_a["id"] in ids
    assert len(ids) == 1


def test_update_and_delete_contract(admin_client):
    client = _create_client(admin_client, email="update-contract@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"])

    resp = admin_client.put(f"/contracts/{contract['id']}", json={"status": "expired"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "expired"

    resp = admin_client.delete(f"/contracts/{contract['id']}")
    assert resp.status_code == 200

    resp = admin_client.get(f"/contracts/{contract['id']}")
    assert resp.status_code == 404


def test_contract_margin_with_no_time_logged(admin_client):
    client = _create_client(admin_client, email="margin-empty@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(admin_client, project["id"], billing_type="hourly", hourly_rate="150.00", value=None)

    resp = admin_client.get(f"/contracts/{contract['id']}/margin")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert float(body["billable_hours"]) == 0
    assert body["hours_value"] == "0.00" or float(body["hours_value"]) == 0


def test_contract_margin_reflects_logged_hours(admin_client):
    client = _create_client(admin_client, email="margin-hours@example.com")
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(
        admin_client, project["id"], billing_type="hourly", hourly_rate="100.00", value="10000.00"
    )

    resp = admin_client.post(
        "/time-entries/",
        json={
            "project_id": project["id"],
            "hours": 5,
            "entry_date": "2026-01-15",
            "billable": True,
            "notes": "Fieldwork",
        },
    )
    assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/contracts/{contract['id']}/margin")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert float(body["billable_hours"]) == 5
    assert float(body["hours_value"]) == 500.0
    assert float(body["remaining_value"]) == 9500.0
