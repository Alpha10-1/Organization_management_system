from tests.test_client_types_and_assignments import _user_id
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_staffing import _create_user

FORECAST_URL = "/capacity/forecast"
SUMMARY_URL = "/capacity/forecast/summary"


def _assign(admin_client, project_id, user_id, allocation_percent):
    resp = admin_client.post(
        f"/projects/{project_id}/assignments",
        json={"user_id": user_id, "allocation_percent": allocation_percent},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _forecast_for_user(admin_client, user_id, **params):
    query = {"user_id": user_id, "months": 3, "start_date": "2027-01-01"}
    query.update(params)
    resp = admin_client.get(FORECAST_URL, params=query)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    return body[0]


# --- weekly hours admin endpoint -------------------------------------------


def test_admin_can_set_weekly_hours(admin_client):
    user = _create_user(admin_client, email="parttime@example.com")
    resp = admin_client.patch(f"/users/{user['email']}/weekly-hours", json={"standard_weekly_hours": "20.00"})
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["standard_weekly_hours"]) == 20.00


def test_weekly_hours_rejects_non_positive(admin_client):
    user = _create_user(admin_client, email="zerohours@example.com")
    resp = admin_client.patch(f"/users/{user['email']}/weekly-hours", json={"standard_weekly_hours": "0"})
    assert resp.status_code == 400


def test_weekly_hours_rejects_over_168(admin_client):
    user = _create_user(admin_client, email="toomanyhours@example.com")
    resp = admin_client.patch(f"/users/{user['email']}/weekly-hours", json={"standard_weekly_hours": "200"})
    assert resp.status_code == 400


def test_new_user_defaults_to_40_weekly_hours(admin_client):
    user = _create_user(admin_client, email="defaulthours@example.com")
    assert float(user["standard_weekly_hours"]) == 40.00


def test_staff_cannot_set_weekly_hours(staff_client, admin_client):
    user = _create_user(admin_client, email="notallowed@example.com")
    resp = staff_client.patch(f"/users/{user['email']}/weekly-hours", json={"standard_weekly_hours": "30"})
    assert resp.status_code == 403


# --- forecast: basic allocation math ----------------------------------------


def test_forecast_reflects_active_assignment(admin_client):
    user = _create_user(admin_client, email="forecast-basic@example.com")
    client = _create_client(admin_client, email="forecast-basic-client@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        status="active",
        start_date="2026-11-01T00:00:00",
        end_date="2027-03-01T00:00:00",
    )
    _assign(admin_client, project["id"], user["id"], 50)

    forecast = _forecast_for_user(admin_client, user["id"])
    jan = next(m for m in forecast["months"] if m["month"] == "2027-01")
    assert jan["allocated_percent"] == 50
    assert jan["status"] == "full"
    assert project["name"] in jan["project_names"]
    # 40 hours/week * ~4.43 weeks in Jan * 50% ~= 88.6 hours
    assert 85 < float(jan["allocated_hours"]) < 92


def test_forecast_excludes_months_outside_project_dates(admin_client):
    user = _create_user(admin_client, email="forecast-outside@example.com")
    client = _create_client(admin_client, email="forecast-outside-client@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        status="active",
        start_date="2027-01-01T00:00:00",
        end_date="2027-01-31T00:00:00",
    )
    _assign(admin_client, project["id"], user["id"], 60)

    forecast = _forecast_for_user(admin_client, user["id"])
    jan = next(m for m in forecast["months"] if m["month"] == "2027-01")
    feb = next(m for m in forecast["months"] if m["month"] == "2027-02")
    assert jan["allocated_percent"] == 60
    assert feb["allocated_percent"] == 0
    assert feb["status"] == "bench"


def test_forecast_open_ended_project_carries_forward(admin_client):
    user = _create_user(admin_client, email="forecast-openended@example.com")
    client = _create_client(admin_client, email="forecast-openended-client@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        status="active",
        start_date="2026-06-01T00:00:00",
        # no end_date -- treated as ongoing indefinitely
    )
    _assign(admin_client, project["id"], user["id"], 30)

    forecast = _forecast_for_user(admin_client, user["id"], months=3, start_date="2027-06-01")
    for month in forecast["months"]:
        assert month["allocated_percent"] == 30


# --- forecast: overbooked / bench status ------------------------------------


def test_forecast_overbooked_status(admin_client):
    user = _create_user(admin_client, email="forecast-over@example.com")
    client = _create_client(admin_client, email="forecast-over-client@example.com")
    project_a = _create_project(
        admin_client, client["id"], status="active", start_date="2027-01-01T00:00:00", end_date="2027-06-01T00:00:00"
    )
    project_b = _create_project(
        admin_client,
        client["id"],
        name="Second Engagement",
        status="active",
        start_date="2027-01-01T00:00:00",
        end_date="2027-06-01T00:00:00",
    )
    _assign(admin_client, project_a["id"], user["id"], 70)
    _assign(admin_client, project_b["id"], user["id"], 60)

    forecast = _forecast_for_user(admin_client, user["id"])
    jan = next(m for m in forecast["months"] if m["month"] == "2027-01")
    assert jan["allocated_percent"] == 130
    assert jan["status"] == "overbooked"
    assert float(jan["available_hours"]) < 0


def test_forecast_no_assignments_is_bench(admin_client):
    user = _create_user(admin_client, email="forecast-bench@example.com")
    forecast = _forecast_for_user(admin_client, user["id"])
    for month in forecast["months"]:
        assert month["status"] == "bench"
        assert month["allocated_percent"] == 0


# --- forecast: excludes non-active engagements and department assignments ---


def test_forecast_excludes_completed_project(admin_client):
    user = _create_user(admin_client, email="forecast-completed@example.com")
    client = _create_client(admin_client, email="forecast-completed-client@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        status="completed",
        start_date="2027-01-01T00:00:00",
        end_date="2027-03-01T00:00:00",
    )
    _assign(admin_client, project["id"], user["id"], 80)

    forecast = _forecast_for_user(admin_client, user["id"])
    for month in forecast["months"]:
        assert month["allocated_percent"] == 0


def test_forecast_ignores_department_only_assignments(admin_client):
    user = _create_user(admin_client, email="forecast-deptonly@example.com")
    client = _create_client(admin_client, email="forecast-deptonly-client@example.com")
    dept = admin_client.post("/departments/", json={"name": "Forecast Dept"}).json()
    admin_client.patch(f"/users/{user['email']}/department", json={"department_id": dept["id"]})

    project = _create_project(
        admin_client,
        client["id"],
        status="active",
        start_date="2027-01-01T00:00:00",
        end_date="2027-03-01T00:00:00",
    )
    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"department_id": dept["id"]},
    )
    assert resp.status_code == 200, resp.text

    forecast = _forecast_for_user(admin_client, user["id"])
    for month in forecast["months"]:
        assert month["allocated_percent"] == 0


# --- forecast: leave reduces capacity but not allocated_percent ------------


def test_forecast_approved_leave_reduces_capacity_hours(admin_client, client):
    manager = _create_user(admin_client, email="forecast-leave-mgr@example.com", position="manager")
    report = _create_user(admin_client, email="forecast-leave-report@example.com", manager_id=manager["id"])

    login = client.post("/auth/login", data={"username": report["email"], "password": "Sup3rSecret!"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    leave_resp = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2027-01-10", "end_date": "2027-01-14"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert leave_resp.status_code == 200, leave_resp.text
    leave = leave_resp.json()

    approve_resp = admin_client.post(f"/leave-requests/{leave['id']}/approve", json={})
    assert approve_resp.status_code == 200, approve_resp.text

    forecast = _forecast_for_user(admin_client, report["id"])
    jan = next(m for m in forecast["months"] if m["month"] == "2027-01")
    assert float(jan["leave_hours"]) > 0
    # Full Jan capacity (no leave) would be ~177 hours (40/wk); 5 PTO days
    # at 8h/day = 40 hours off, so capacity should sit meaningfully below that.
    assert float(jan["capacity_hours"]) < 177 - 30


# --- forecast: filters -------------------------------------------------------


def test_forecast_department_filter(admin_client):
    dept = admin_client.post("/departments/", json={"name": "Filter Dept"}).json()
    user_in = _create_user(admin_client, email="filter-in@example.com", department_id=dept["id"])
    user_out = _create_user(admin_client, email="filter-out@example.com")

    resp = admin_client.get(FORECAST_URL, params={"department_id": dept["id"], "months": 1, "start_date": "2027-01-01"})
    assert resp.status_code == 200, resp.text
    ids = {row["user_id"] for row in resp.json()}
    assert user_in["id"] in ids
    assert user_out["id"] not in ids


def test_forecast_unknown_department_404(admin_client):
    resp = admin_client.get(FORECAST_URL, params={"department_id": 999999, "months": 1})
    assert resp.status_code == 404


def test_forecast_months_out_of_range_rejected(admin_client):
    resp = admin_client.get(FORECAST_URL, params={"months": 0})
    assert resp.status_code == 422

    resp = admin_client.get(FORECAST_URL, params={"months": 25})
    assert resp.status_code == 422


def test_forecast_requires_auth(client):
    resp = client.get(FORECAST_URL)
    assert resp.status_code == 401


# --- forecast summary ---------------------------------------------------------


def test_forecast_summary_lists_overbooked_and_bench(admin_client):
    over_user = _create_user(admin_client, email="summary-over@example.com")
    bench_user = _create_user(admin_client, email="summary-bench@example.com")
    client = _create_client(admin_client, email="summary-client@example.com")
    project_a = _create_project(
        admin_client,
        client["id"],
        status="active",
        start_date="2027-01-01T00:00:00",
        end_date="2027-06-01T00:00:00",
    )
    project_b = _create_project(
        admin_client,
        client["id"],
        name="Summary Second Engagement",
        status="active",
        start_date="2027-01-01T00:00:00",
        end_date="2027-06-01T00:00:00",
    )
    _assign(admin_client, project_a["id"], over_user["id"], 70)
    _assign(admin_client, project_b["id"], over_user["id"], 60)

    resp = admin_client.get(SUMMARY_URL, params={"months": 1, "start_date": "2027-01-01"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["months"]) == 1
    jan = body["months"][0]
    assert jan["month"] == "2027-01"
    assert over_user["name"] in jan["overbooked_users"]
    assert bench_user["name"] in jan["bench_users"]
    assert jan["overbooked_count"] >= 1
    assert jan["bench_count"] >= 1
