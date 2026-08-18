import uuid

from tests.conftest import ADMIN_EMAIL
from tests.test_contracts import _create_contract
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_department(admin_client, **overrides):
    payload = {"name": _unique_name("Dept")}
    payload.update(overrides)
    resp = admin_client.post("/departments/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_user(admin_client, **overrides):
    payload = {
        "name": "Dept User",
        "email": f"deptuser-{uuid.uuid4().hex[:8]}@example.com",
        "password": "Sup3rSecret!",
        "role": "staff",
    }
    payload.update(overrides)
    resp = admin_client.post("/users/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_department_with_cost_center(admin_client):
    department = _create_department(admin_client, annual_budget="250000.00", cost_center_code="CC-100")
    assert department["cost_center_code"] == "CC-100"
    assert float(department["annual_budget"]) == 250000.00


def test_admin_can_update_department_budget(admin_client):
    department = _create_department(admin_client)
    resp = admin_client.put(f"/departments/{department['id']}", json={"annual_budget": "300000.00"})
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["annual_budget"]) == 300000.00


def test_staff_who_is_not_department_head_cannot_update_department(staff_client, admin_client):
    department = _create_department(admin_client)
    resp = staff_client.put(f"/departments/{department['id']}", json={"annual_budget": "999.00"})
    assert resp.status_code == 403


def test_department_head_can_update_own_department(admin_client, staff_client):
    from tests.conftest import STAFF_EMAIL

    staff_user = admin_client.get("/users/").json()
    head = next(u for u in staff_user if u["email"] == STAFF_EMAIL)

    department = _create_department(admin_client, department_head_user_id=head["id"])
    resp = staff_client.put(f"/departments/{department['id']}", json={"cost_center_code": "CC-HEAD"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["cost_center_code"] == "CC-HEAD"


def test_department_dashboard_basic_shape(admin_client):
    department = _create_department(admin_client, annual_budget="100000.00")
    resp = admin_client.get(f"/departments/{department['id']}/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["department_id"] == department["id"]
    assert body["staff_count"] == 0
    assert body["active_engagement_count"] == 0
    assert float(body["revenue_to_date"]) == 0.0


def test_department_dashboard_counts_staff_and_bench(admin_client):
    department = _create_department(admin_client)
    _create_user(admin_client, department_id=department["id"])
    _create_user(admin_client, department_id=department["id"])

    resp = admin_client.get(f"/departments/{department['id']}/dashboard")
    body = resp.json()
    assert body["staff_count"] == 2
    assert body["bench_count"] == 2  # no assignments yet


def test_department_dashboard_active_engagements_and_revenue(admin_client):
    department = _create_department(admin_client, annual_budget="10000.00")
    client = _create_client(admin_client, email="dept-dash@example.com", department_id=department["id"])
    project = _create_project(admin_client, client["id"], status="active")
    _create_contract(admin_client, project["id"], value="15000.00", status="signed")

    resp = admin_client.get(f"/departments/{department['id']}/dashboard")
    body = resp.json()
    assert body["active_engagement_count"] == 1
    assert float(body["revenue_to_date"]) == 15000.00
    assert float(body["budget_variance"]) == 5000.00


def test_department_dashboard_requires_valid_department(admin_client):
    resp = admin_client.get("/departments/999999/dashboard")
    assert resp.status_code == 404
