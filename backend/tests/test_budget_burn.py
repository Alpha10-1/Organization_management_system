from tests.test_contracts import _create_contract
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_time_entries import _create_time_entry


def test_budget_burn_no_budget_set(admin_client):
    client = _create_client(admin_client, email="burn-no-budget@example.com")
    project = _create_project(admin_client, client["id"], budget=None)

    resp = admin_client.get(f"/projects/{project['id']}/budget")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "no_budget"
    assert body["cost_to_date"] is None
    assert body["percent_consumed"] is None


def test_budget_burn_hours_only_without_hourly_rate(admin_client):
    client = _create_client(admin_client, email="burn-hours-only@example.com")
    project = _create_project(admin_client, client["id"], budget="10000.00")
    _create_time_entry(admin_client, project["id"], hours="5.0")

    resp = admin_client.get(f"/projects/{project['id']}/budget")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "hours_only"
    assert body["cost_to_date"] is None
    assert float(body["billable_hours"]) == 5.0


def test_budget_burn_computes_cost_and_percent(admin_client):
    client = _create_client(admin_client, email="burn-cost@example.com")
    project = _create_project(admin_client, client["id"], budget="1000.00")
    _create_contract(
        admin_client,
        project["id"],
        billing_type="hourly",
        hourly_rate="100.00",
        value=None,
        status="signed",
    )
    _create_time_entry(admin_client, project["id"], hours="5.0", billable=True)
    _create_time_entry(admin_client, project["id"], hours="2.0", billable=False)

    resp = admin_client.get(f"/projects/{project['id']}/budget")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["effective_hourly_rate"] == "100.00"
    assert float(body["cost_to_date"]) == 500.0
    assert body["percent_consumed"] == 50.0
    assert body["status"] == "on_track"
    assert body["alert"] is False


def test_budget_burn_alert_thresholds(admin_client):
    client = _create_client(admin_client, email="burn-alert@example.com")
    project = _create_project(admin_client, client["id"], budget="1000.00")
    _create_contract(
        admin_client, project["id"], billing_type="hourly", hourly_rate="100.00", value=None, status="signed"
    )
    _create_time_entry(admin_client, project["id"], hours="9.0", billable=True)  # 900/1000 = 90%

    resp = admin_client.get(f"/projects/{project['id']}/budget")
    body = resp.json()
    assert body["status"] == "at_risk"
    assert body["alert"] is True

    resp = admin_client.get(f"/projects/{project['id']}/budget?alert_threshold_percent=95")
    body = resp.json()
    assert body["status"] == "on_track"
    assert body["alert"] is False


def test_budget_burn_over_budget(admin_client):
    client = _create_client(admin_client, email="burn-over@example.com")
    project = _create_project(admin_client, client["id"], budget="500.00")
    _create_contract(
        admin_client, project["id"], billing_type="hourly", hourly_rate="100.00", value=None, status="signed"
    )
    _create_time_entry(admin_client, project["id"], hours="10.0", billable=True)

    resp = admin_client.get(f"/projects/{project['id']}/budget")
    body = resp.json()
    assert body["status"] == "over_budget"
    assert body["alert"] is True


def test_budget_burn_requires_valid_project(admin_client):
    resp = admin_client.get("/projects/999999/budget")
    assert resp.status_code == 404
