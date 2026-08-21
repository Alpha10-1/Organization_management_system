from datetime import datetime, timedelta, timezone

from tests.test_contracts import _create_contract
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_time_entries import _create_time_entry


def test_forecast_low_risk_for_healthy_engagement(admin_client):
    client = _create_client(admin_client, email="risk-green@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low")

    resp = admin_client.get(f"/projects/{project['id']}/risk-forecast")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_health"] == "green"
    assert body["predicted_health"] == "green"
    assert body["risk_score"] < 30
    assert body["leading_indicator"] is False
    # No prior snapshot exists yet on a brand-new engagement.
    assert body["trend"] == "insufficient_data"


def test_forecast_high_score_for_high_risk_engagement(admin_client):
    client = _create_client(admin_client, email="risk-high@example.com")
    project = _create_project(admin_client, client["id"], risk_level="high")

    resp = admin_client.get(f"/projects/{project['id']}/risk-forecast")
    body = resp.json()
    assert body["predicted_health"] == "red"
    assert body["risk_score"] >= 30
    assert any("Risk level" in s for s in body["signals"])


def test_forecast_records_snapshot_and_computes_trend(admin_client):
    from app.db.session import SessionLocal
    from app.models.project import Project as ProjectModel
    from app.core.risk_prediction import record_snapshot
    from datetime import date as date_type, timedelta as td

    client = _create_client(admin_client, email="risk-trend@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low")

    # Backdate a healthy baseline snapshot directly (the endpoint only ever
    # snapshots "today", so a same-day trend test needs a manufactured
    # older baseline to compare against).
    with SessionLocal() as db:
        project_row = db.query(ProjectModel).filter(ProjectModel.id == project["id"]).first()
        baseline = record_snapshot(db, project_row, on=date_type.today() - td(days=10))
        assert baseline.risk_score < 10

    # Escalate risk and pile on overdue tasks so today's score is clearly higher.
    resp = admin_client.put(f"/projects/{project['id']}", json={"risk_level": "high"})
    assert resp.status_code == 200, resp.text

    for i in range(3):
        past_due = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
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

    resp = admin_client.get(f"/projects/{project['id']}/risk-forecast?lookback_days=7")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trend"] == "worsening"
    assert body["baseline_score"] < body["risk_score"]
    assert body["score_delta"] > 0


def test_forecast_requires_existing_project(admin_client):
    resp = admin_client.get("/projects/999999/risk-forecast")
    assert resp.status_code == 404


def test_at_risk_engagements_report_flags_worsening_engagement(admin_client):
    client = _create_client(admin_client, email="risk-report@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low", status="active")

    # Baseline low-risk snapshot from 10 days ago.
    from app.db.session import SessionLocal
    from app.models.project import Project as ProjectModel
    from app.core.risk_prediction import record_snapshot
    from datetime import date as date_type, timedelta as td

    with SessionLocal() as db:
        project_row = db.query(ProjectModel).filter(ProjectModel.id == project["id"]).first()
        record_snapshot(db, project_row, on=date_type.today() - td(days=10))

    resp = admin_client.put(f"/projects/{project['id']}", json={"risk_level": "high"})
    assert resp.status_code == 200, resp.text

    resp = admin_client.get("/reports/at-risk-engagements?lookback_days=7")
    assert resp.status_code == 200, resp.text
    ids = [row["project_id"] for row in resp.json()]
    assert project["id"] in ids


def test_at_risk_engagements_report_visible_to_any_authenticated_user(staff_client, admin_client):
    """Unrestricted for any authenticated user, matching every other
    firm-wide report in this file (compliance_dashboard, capacity_dashboard,
    realization_report) -- not scoped to admins or to a partner/manager
    relationship on the engagement."""
    from app.db.session import SessionLocal
    from app.models.project import Project as ProjectModel
    from app.core.risk_prediction import record_snapshot
    from datetime import date as date_type, timedelta as td

    client = _create_client(admin_client, email="risk-scope@example.com")
    project = _create_project(admin_client, client["id"], risk_level="low", status="active")

    with SessionLocal() as db:
        project_row = db.query(ProjectModel).filter(ProjectModel.id == project["id"]).first()
        record_snapshot(db, project_row, on=date_type.today() - td(days=10))

    resp = admin_client.put(f"/projects/{project['id']}", json={"risk_level": "high"})
    assert resp.status_code == 200, resp.text

    resp = staff_client.get("/reports/at-risk-engagements?lookback_days=7&min_score=0")
    assert resp.status_code == 200, resp.text
    ids = [row["project_id"] for row in resp.json()]
    assert project["id"] in ids


def test_leading_indicator_flags_before_health_badge_turns_red(admin_client):
    """A concrete scenario where the forecast's predicted_health is red
    while today's actual health badge is still amber -- the leading
    indicator the roadmap calls out."""
    client = _create_client(admin_client, email="risk-leading@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        risk_level="medium",
        status="active",
        budget="1000.00",
        start_date=datetime.now(timezone.utc).isoformat(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=200)).isoformat(),
    )
    _create_contract(
        admin_client, project["id"], billing_type="hourly", hourly_rate="100.00", value=None, status="signed"
    )
    # 8.5h billed at $100/h against a $1000 budget = 85% consumed (at_risk,
    # not over_budget), while only ~1 day of a 200-day timeline has elapsed
    # -- a sharp budget-burn velocity spike.
    _create_time_entry(admin_client, project["id"], hours="8.5", billable=True)

    past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    resp = admin_client.post(
        "/tasks/",
        json={"title": "Overdue task", "project_id": project["id"], "client_id": client["id"], "due_date": past_due},
    )
    assert resp.status_code == 200, resp.text

    resp = admin_client.post(
        "/milestones/",
        json={
            "project_id": project["id"],
            "name": "Interim review",
            "status": "pending",
            "due_date": past_due,
        },
    )
    assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/projects/{project['id']}/health")
    assert resp.status_code == 200, resp.text
    health = resp.json()
    assert health["health"] in ("amber",)  # not yet red

    resp = admin_client.get(f"/projects/{project['id']}/risk-forecast")
    assert resp.status_code == 200, resp.text
    forecast = resp.json()
    assert forecast["current_health"] == "amber"
    assert forecast["predicted_health"] == "red"
    assert forecast["leading_indicator"] is True
