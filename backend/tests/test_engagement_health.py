from datetime import datetime, timedelta, timezone

from tests.test_contracts import _create_contract
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_time_entries import _create_time_entry


def test_health_green_for_healthy_engagement(admin_client):
    client = _create_client(admin_client, email="health-green@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low")

    resp = admin_client.get(f"/projects/{project['id']}/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["health"] == "green"
    assert body["overdue_task_count"] == 0
    assert body["timeline_slipped"] is False


def test_health_red_for_high_risk_engagement(admin_client):
    client = _create_client(admin_client, email="health-red-risk@example.com")
    project = _create_project(admin_client, client["id"], risk_level="high")

    resp = admin_client.get(f"/projects/{project['id']}/health")
    body = resp.json()
    assert body["health"] == "red"
    assert any("Risk level" in reason for reason in body["reasons"])


def test_health_red_for_overdue_tasks(admin_client):
    client = _create_client(admin_client, email="health-red-tasks@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low")

    past_due = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    for i in range(3):
        resp = admin_client.post(
            "/tasks/",
            json={
                "title": f"Overdue task {i}",
                "project_id": project["id"],
                "client_id": client["id"],
                "due_date": past_due,
            },
        )
        assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/projects/{project['id']}/health")
    body = resp.json()
    assert body["overdue_task_count"] == 3
    assert body["health"] == "red"


def test_health_red_for_timeline_slippage(admin_client):
    client = _create_client(admin_client, email="health-red-timeline@example.com")
    past_end = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    project = _create_project(
        admin_client,
        client["id"],
        risk_level="low",
        start_date=(datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        end_date=past_end,
        status="active",
    )

    resp = admin_client.get(f"/projects/{project['id']}/health")
    body = resp.json()
    assert body["timeline_slipped"] is True
    assert body["health"] == "red"


def test_health_amber_for_at_risk_budget(admin_client):
    client = _create_client(admin_client, email="health-amber-budget@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low", budget="1000.00")
    _create_contract(
        admin_client, project["id"], billing_type="hourly", hourly_rate="100.00", value=None, status="signed"
    )
    _create_time_entry(admin_client, project["id"], hours="9.0", billable=True)  # 90% consumed

    resp = admin_client.get(f"/projects/{project['id']}/health")
    body = resp.json()
    assert body["budget_status"] == "at_risk"
    assert body["health"] == "amber"


def test_health_requires_valid_project(admin_client):
    resp = admin_client.get("/projects/999999/health")
    assert resp.status_code == 404
