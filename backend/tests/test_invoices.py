from tests.conftest import STAFF_EMAIL
from tests.test_contracts import _create_contract
from tests.test_department_kpis import _create_department, _create_user
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_time_entries import _create_time_entry


def _setup_project(admin_client, email, **contract_overrides):
    client = _create_client(admin_client, email=email)
    project = _create_project(admin_client, client["id"])
    contract = _create_contract(
        admin_client,
        project["id"],
        billing_type="hourly",
        hourly_rate="200.00",
        value=None,
        **contract_overrides,
    )
    return client, project, contract


def _login_bearer(client, email, password="Sup3rSecret!"):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(client, email, password="Sup3rSecret!"):
    return {"Authorization": f"Bearer {_login_bearer(client, email, password)}"}


# --- Rate resolution & WIP --------------------------------------------------


def test_wip_values_hours_at_contract_rate(admin_client):
    _, project, _ = _setup_project(admin_client, "wip-contract-rate@example.com")
    _create_time_entry(admin_client, project["id"], hours="3.0", billable=True)
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=False)  # non-billable excluded

    resp = admin_client.get("/invoices/wip", params={"project_id": project["id"]})
    assert resp.status_code == 200, resp.text
    wip = resp.json()
    assert wip["total_hours"] == "3.00"
    assert wip["valued_hours"] == "3.00"
    assert wip["unrated_hours"] == "0.00"
    assert wip["wip_value"] == "600.00"
    assert wip["entry_count"] == 1


def test_wip_falls_back_to_user_standard_rate_without_contract_rate(admin_client):
    client = _create_client(admin_client, email="wip-userrate@example.com")
    project = _create_project(admin_client, client["id"])
    # fixed_fee contract, no hourly_rate -> falls back to the logging user's rate
    _create_contract(admin_client, project["id"], billing_type="fixed_fee", value="10000.00")

    rated_user = _create_user(admin_client)
    admin_resp = admin_client.patch(
        f"/users/{rated_user['email']}/billing-rate", json={"standard_billing_rate": "150.00"}
    )
    assert admin_resp.status_code == 200, admin_resp.text

    _create_time_entry(admin_client, project["id"], hours="4.0", billable=True, user_email=rated_user["email"])

    resp = admin_client.get("/invoices/wip", params={"project_id": project["id"]})
    wip = resp.json()
    assert wip["wip_value"] == "600.00"


def test_wip_marks_unrated_hours_when_no_rate_available(admin_client):
    client = _create_client(admin_client, email="wip-unrated@example.com")
    project = _create_project(admin_client, client["id"])
    _create_contract(admin_client, project["id"], billing_type="fixed_fee", value="10000.00")
    # admin user has no standard_billing_rate set and contract has no hourly_rate
    _create_time_entry(admin_client, project["id"], hours="5.0", billable=True)

    resp = admin_client.get("/invoices/wip", params={"project_id": project["id"]})
    wip = resp.json()
    assert wip["total_hours"] == "5.00"
    assert wip["valued_hours"] == "0.00"
    assert wip["unrated_hours"] == "5.00"
    assert wip["wip_value"] == "0.00"


def test_wip_requires_valid_project(admin_client):
    resp = admin_client.get("/invoices/wip", params={"project_id": 999999})
    assert resp.status_code == 404


# --- Invoice generation -----------------------------------------------------


def test_generate_invoice_from_all_wip(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-generate@example.com")
    _create_time_entry(admin_client, project["id"], hours="3.0", billable=True)
    _create_time_entry(admin_client, project["id"], hours="1.0", billable=True)
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=False)

    resp = admin_client.post("/invoices/", json={"project_id": project["id"], "contract_id": contract["id"]})
    assert resp.status_code == 200, resp.text
    invoice = resp.json()

    assert invoice["status"] == "draft"
    assert invoice["subtotal"] == "800.00"  # 4 billable hours * 200
    assert invoice["total_amount"] == "800.00"
    assert len(invoice["line_items"]) == 2
    assert invoice["invoice_number"].startswith("INV-")

    # WIP is now empty for those entries
    wip = admin_client.get("/invoices/wip", params={"project_id": project["id"]}).json()
    assert wip["total_hours"] == "0.00"


def test_generate_invoice_from_explicit_time_entry_selection(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-explicit@example.com")
    entry1 = _create_time_entry(admin_client, project["id"], hours="3.0", billable=True)
    entry2 = _create_time_entry(admin_client, project["id"], hours="1.0", billable=True)

    resp = admin_client.post(
        "/invoices/",
        json={"project_id": project["id"], "contract_id": contract["id"], "time_entry_ids": [entry1["id"]]},
    )
    assert resp.status_code == 200, resp.text
    invoice = resp.json()
    assert invoice["subtotal"] == "600.00"

    # entry2 remains in WIP
    wip = admin_client.get("/invoices/wip", params={"project_id": project["id"]}).json()
    assert wip["total_hours"] == "1.00"
    assert wip["entry_count"] == 1


def test_generate_invoice_with_manual_line_item_only(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-manual@example.com")

    resp = admin_client.post(
        "/invoices/",
        json={
            "project_id": project["id"],
            "contract_id": contract["id"],
            "time_entry_ids": [],
            "manual_line_items": [{"description": "Milestone 1 fixed fee", "amount": "2500.00"}],
        },
    )
    assert resp.status_code == 200, resp.text
    invoice = resp.json()
    assert invoice["subtotal"] == "2500.00"
    assert len(invoice["line_items"]) == 1
    assert invoice["line_items"][0]["time_entry_id"] is None


def test_generate_invoice_applies_tax_amount(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-tax@example.com")
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=True)

    resp = admin_client.post(
        "/invoices/",
        json={"project_id": project["id"], "contract_id": contract["id"], "tax_amount": "40.00"},
    )
    invoice = resp.json()
    assert invoice["subtotal"] == "400.00"
    assert invoice["tax_amount"] == "40.00"
    assert invoice["total_amount"] == "440.00"


def test_generate_invoice_rejects_already_invoiced_entry(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-double@example.com")
    entry = _create_time_entry(admin_client, project["id"], hours="2.0", billable=True)

    resp = admin_client.post(
        "/invoices/",
        json={"project_id": project["id"], "contract_id": contract["id"], "time_entry_ids": [entry["id"]]},
    )
    assert resp.status_code == 200

    resp2 = admin_client.post(
        "/invoices/",
        json={"project_id": project["id"], "contract_id": contract["id"], "time_entry_ids": [entry["id"]]},
    )
    assert resp2.status_code == 400


def test_generate_invoice_rejects_entry_from_other_project(admin_client):
    _, project_a, contract_a = _setup_project(admin_client, "inv-cross-a@example.com")
    _, project_b, _ = _setup_project(admin_client, "inv-cross-b@example.com")
    entry_b = _create_time_entry(admin_client, project_b["id"], hours="2.0", billable=True)

    resp = admin_client.post(
        "/invoices/",
        json={"project_id": project_a["id"], "contract_id": contract_a["id"], "time_entry_ids": [entry_b["id"]]},
    )
    assert resp.status_code == 400


def test_generate_invoice_rejects_when_nothing_to_bill(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-empty@example.com")
    resp = admin_client.post(
        "/invoices/", json={"project_id": project["id"], "contract_id": contract["id"], "time_entry_ids": []}
    )
    assert resp.status_code == 422


def test_generate_invoice_rejects_unknown_project(admin_client):
    resp = admin_client.post("/invoices/", json={"project_id": 999999})
    assert resp.status_code == 404


def test_generate_invoice_rejects_contract_not_matching_project(admin_client):
    _, project_a, _ = _setup_project(admin_client, "inv-mismatch-a@example.com")
    _, _, contract_b = _setup_project(admin_client, "inv-mismatch-b@example.com")

    resp = admin_client.post("/invoices/", json={"project_id": project_a["id"], "contract_id": contract_b["id"]})
    assert resp.status_code == 404


# --- Invoice lifecycle -------------------------------------------------------


def _generate_invoice(admin_client, project_id, contract_id, hours="2.0"):
    _create_time_entry(admin_client, project_id, hours=hours, billable=True)
    resp = admin_client.post("/invoices/", json={"project_id": project_id, "contract_id": contract_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_send_invoice_transitions_draft_to_sent(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-send@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"])

    resp = admin_client.post(f"/invoices/{invoice['id']}/send")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "sent"


def test_send_invoice_rejects_non_draft(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-send-twice@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"])
    admin_client.post(f"/invoices/{invoice['id']}/send")

    resp = admin_client.post(f"/invoices/{invoice['id']}/send")
    assert resp.status_code == 400


def test_update_invoice_only_allowed_while_draft(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-update@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"])

    resp = admin_client.patch(f"/invoices/{invoice['id']}", json={"notes": "Net 30"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["notes"] == "Net 30"

    admin_client.post(f"/invoices/{invoice['id']}/send")
    resp2 = admin_client.patch(f"/invoices/{invoice['id']}", json={"notes": "too late"})
    assert resp2.status_code == 400


def test_record_full_payment_marks_invoice_paid(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-pay-full@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"], hours="2.0")  # $400
    admin_client.post(f"/invoices/{invoice['id']}/send")

    resp = admin_client.post(f"/invoices/{invoice['id']}/record-payment", json={"amount_paid": "400.00"})
    assert resp.status_code == 200, resp.text
    paid = resp.json()
    assert paid["status"] == "paid"
    assert paid["amount_paid"] == "400.00"


def test_record_partial_payment_keeps_invoice_sent(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-pay-partial@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"], hours="2.0")  # $400
    admin_client.post(f"/invoices/{invoice['id']}/send")

    resp = admin_client.post(f"/invoices/{invoice['id']}/record-payment", json={"amount_paid": "150.00"})
    assert resp.status_code == 200, resp.text
    partial = resp.json()
    assert partial["status"] == "sent"
    assert partial["amount_paid"] == "150.00"


def test_record_payment_rejects_draft_invoice(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-pay-draft@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"])

    resp = admin_client.post(f"/invoices/{invoice['id']}/record-payment", json={"amount_paid": "100.00"})
    assert resp.status_code == 400


def test_void_invoice_releases_time_entries_back_to_wip(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-void@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"], hours="3.0")

    wip_before = admin_client.get("/invoices/wip", params={"project_id": project["id"]}).json()
    assert wip_before["total_hours"] == "0.00"

    resp = admin_client.post(f"/invoices/{invoice['id']}/void", json={"reason": "wrong client billed"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "void"

    wip_after = admin_client.get("/invoices/wip", params={"project_id": project["id"]}).json()
    assert wip_after["total_hours"] == "3.00"


def test_void_invoice_rejects_when_payment_recorded(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-void-paid@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"], hours="2.0")
    admin_client.post(f"/invoices/{invoice['id']}/send")
    admin_client.post(f"/invoices/{invoice['id']}/record-payment", json={"amount_paid": "100.00"})

    resp = admin_client.post(f"/invoices/{invoice['id']}/void")
    assert resp.status_code == 400


def test_delete_draft_invoice_releases_time_entries(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-delete@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"], hours="1.5")

    resp = admin_client.delete(f"/invoices/{invoice['id']}")
    assert resp.status_code == 200, resp.text

    wip = admin_client.get("/invoices/wip", params={"project_id": project["id"]}).json()
    assert wip["total_hours"] == "1.50"

    get_resp = admin_client.get(f"/invoices/{invoice['id']}")
    assert get_resp.status_code == 404


def test_delete_invoice_rejects_non_draft(admin_client):
    _, project, contract = _setup_project(admin_client, "inv-delete-sent@example.com")
    invoice = _generate_invoice(admin_client, project["id"], contract["id"])
    admin_client.post(f"/invoices/{invoice['id']}/send")

    resp = admin_client.delete(f"/invoices/{invoice['id']}")
    assert resp.status_code == 400


def test_list_invoices_filters_by_project_and_status(admin_client):
    _, project_a, contract_a = _setup_project(admin_client, "inv-list-a@example.com")
    _, project_b, contract_b = _setup_project(admin_client, "inv-list-b@example.com")
    inv_a = _generate_invoice(admin_client, project_a["id"], contract_a["id"])
    _generate_invoice(admin_client, project_b["id"], contract_b["id"])
    admin_client.post(f"/invoices/{inv_a['id']}/send")

    resp = admin_client.get("/invoices/", params={"project_id": project_a["id"]})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert inv_a["id"] in ids
    assert len(resp.json()) == 1

    resp2 = admin_client.get("/invoices/", params={"status": "sent"})
    assert all(i["status"] == "sent" for i in resp2.json())


# --- Permissions ---------------------------------------------------------


def test_staff_outside_department_cannot_generate_invoice(admin_client, client):
    dept = _create_department(admin_client)
    outsider = _create_user(admin_client)  # no department

    org_client = _create_client(admin_client, email="inv-perm-client@example.com", department_id=dept["id"])
    project = _create_project(admin_client, org_client["id"])
    contract = _create_contract(admin_client, project["id"], billing_type="hourly", hourly_rate="150.00", value=None)
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=True)

    headers = _auth_headers(client, outsider["email"])
    resp = client.post(
        "/invoices/", json={"project_id": project["id"], "contract_id": contract["id"]}, headers=headers
    )
    assert resp.status_code == 403


def test_staff_in_department_can_generate_invoice(admin_client, client):
    dept = _create_department(admin_client)
    member = _create_user(admin_client, department_id=dept["id"])

    org_client = _create_client(admin_client, email="inv-perm-member@example.com", department_id=dept["id"])
    project = _create_project(admin_client, org_client["id"])
    contract = _create_contract(admin_client, project["id"], billing_type="hourly", hourly_rate="150.00", value=None)
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=True)

    headers = _auth_headers(client, member["email"])
    resp = client.post(
        "/invoices/", json={"project_id": project["id"], "contract_id": contract["id"]}, headers=headers
    )
    assert resp.status_code == 200, resp.text


def test_only_admin_can_set_billing_rate(admin_client, staff_client):
    resp = staff_client.patch("/users/admin@org.com/billing-rate", json={"standard_billing_rate": "999.00"})
    assert resp.status_code == 403


# --- Realization rate report -------------------------------------------------


def test_realization_report_by_project(admin_client):
    _, project, contract = _setup_project(admin_client, "real-project@example.com")
    _create_time_entry(admin_client, project["id"], hours="5.0", billable=True, entry_date="2026-08-01")
    invoice = admin_client.post(
        "/invoices/", json={"project_id": project["id"], "contract_id": contract["id"]}
    ).json()
    admin_client.post(f"/invoices/{invoice['id']}/send")

    resp = admin_client.get(
        "/reports/realization",
        params={"group_by": "project", "start_date": "2026-08-01", "end_date": "2026-08-31"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    row = next(r for r in data["rows"] if r["key"] == str(project["id"]))
    assert row["worked_value"] == "1000.00"
    assert row["billed_value"] == "1000.00"
    assert row["realization_rate"] == "1.0000"


def test_realization_report_reflects_partial_billing(admin_client):
    _, project, contract = _setup_project(admin_client, "real-partial@example.com")
    entry1 = _create_time_entry(admin_client, project["id"], hours="4.0", billable=True, entry_date="2026-08-02")
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=True, entry_date="2026-08-03")

    invoice = admin_client.post(
        "/invoices/",
        json={"project_id": project["id"], "contract_id": contract["id"], "time_entry_ids": [entry1["id"]]},
    ).json()
    admin_client.post(f"/invoices/{invoice['id']}/send")

    resp = admin_client.get(
        "/reports/realization",
        params={"group_by": "project", "project_id": project["id"]},
    )
    row = resp.json()["rows"][0]
    # worked = (4+2)*200 = 1200, billed = 4*200 = 800
    assert row["worked_value"] == "1200.00"
    assert row["billed_value"] == "800.00"
    assert row["realization_rate"] == "0.6667"


def test_realization_report_by_partner(admin_client):
    partner = _create_user(admin_client, email="partner@org.com", name="Pat Partner")
    client_obj = _create_client(admin_client, email="real-partner@example.com")
    project = _create_project(
        admin_client,
        client_obj["id"],
        engagement_partner_email=partner["email"],
    )
    contract = _create_contract(admin_client, project["id"], billing_type="hourly", hourly_rate="100.00", value=None)
    _create_time_entry(admin_client, project["id"], hours="10.0", billable=True, entry_date="2026-08-05")

    resp = admin_client.get("/reports/realization", params={"group_by": "partner"})
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["rows"] if r["key"] == "partner@org.com")
    assert row["label"] == "Pat Partner"
    assert row["worked_value"] == "1000.00"


def test_void_invoice_removes_it_from_realization_billed_value(admin_client):
    _, project, contract = _setup_project(admin_client, "real-void@example.com")
    _create_time_entry(admin_client, project["id"], hours="3.0", billable=True, entry_date="2026-08-06")
    invoice = admin_client.post(
        "/invoices/", json={"project_id": project["id"], "contract_id": contract["id"]}
    ).json()
    admin_client.post(f"/invoices/{invoice['id']}/void")

    resp = admin_client.get("/reports/realization", params={"group_by": "project", "project_id": project["id"]})
    row = resp.json()["rows"][0]
    assert row["billed_value"] == "0.00"
    assert row["worked_value"] == "600.00"
