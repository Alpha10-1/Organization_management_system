import uuid

from tests.conftest import ADMIN_EMAIL, STAFF_EMAIL


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _create_user(admin_client, **overrides):
    payload = {
        "name": "Test User",
        "email": _unique_email("staffing"),
        "password": "Sup3rSecret!",
        "role": "staff",
    }
    payload.update(overrides)
    resp = admin_client.post("/users/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Position -------------------------------------------------------------


def test_create_user_with_valid_position(admin_client):
    user = _create_user(admin_client, position="senior_associate")
    assert user["position"] == "senior_associate"


def test_create_user_with_invalid_position_rejected(admin_client):
    resp = admin_client.post(
        "/users/",
        json={
            "name": "Bad Position",
            "email": _unique_email("badpos"),
            "password": "Sup3rSecret!",
            "position": "wizard",
        },
    )
    assert resp.status_code == 400


def test_update_position_via_dedicated_endpoint(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.patch(f"/users/{user['email']}/position", json={"position": "manager"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["position"] == "manager"


def test_update_position_invalid_value_rejected(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.patch(f"/users/{user['email']}/position", json={"position": "ceo"})
    assert resp.status_code == 400


def test_staff_cannot_update_position(staff_client):
    resp = staff_client.patch(f"/users/{STAFF_EMAIL}/position", json={"position": "partner"})
    assert resp.status_code == 403


# --- Manager hierarchy ------------------------------------------------------


def test_assign_manager_via_create(admin_client):
    manager = _create_user(admin_client, position="manager")
    report = _create_user(admin_client, manager_id=manager["id"])
    assert report["manager_id"] == manager["id"]


def test_assign_manager_via_position_endpoint(admin_client):
    manager = _create_user(admin_client, position="senior_manager")
    report = _create_user(admin_client)

    resp = admin_client.patch(
        f"/users/{report['email']}/position", json={"manager_id": manager["id"]}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["manager_id"] == manager["id"]


def test_clear_manager_with_explicit_null(admin_client):
    manager = _create_user(admin_client)
    report = _create_user(admin_client, manager_id=manager["id"])

    resp = admin_client.patch(f"/users/{report['email']}/position", json={"manager_id": None})
    assert resp.status_code == 200, resp.text
    assert resp.json()["manager_id"] is None


def test_user_cannot_manage_self(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.patch(
        f"/users/{user['email']}/position", json={"manager_id": user["id"]}
    )
    assert resp.status_code == 400


def test_manager_must_exist(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.patch(
        f"/users/{user['email']}/position", json={"manager_id": 999999}
    )
    assert resp.status_code == 400


def test_manager_cycle_rejected(admin_client):
    a = _create_user(admin_client)
    b = _create_user(admin_client, manager_id=a["id"])

    # a reports to b would create a 2-cycle (a -> b -> a)
    resp = admin_client.patch(f"/users/{a['email']}/position", json={"manager_id": b["id"]})
    assert resp.status_code == 400
    assert "cycle" in resp.json()["detail"].lower()


def test_manager_transitive_cycle_rejected(admin_client):
    a = _create_user(admin_client)
    b = _create_user(admin_client, manager_id=a["id"])
    c = _create_user(admin_client, manager_id=b["id"])

    # a reports to c would create a -> c -> b -> a cycle
    resp = admin_client.patch(f"/users/{a['email']}/position", json={"manager_id": c["id"]})
    assert resp.status_code == 400


# --- Org chart --------------------------------------------------------------


def test_org_chart_nests_reports_under_manager(admin_client):
    manager = _create_user(admin_client, position="director")
    report = _create_user(admin_client, manager_id=manager["id"])

    resp = admin_client.get("/users/org-chart")
    assert resp.status_code == 200, resp.text
    tree = resp.json()

    def _find(nodes, user_id):
        for node in nodes:
            if node["id"] == user_id:
                return node
            found = _find(node["reports"], user_id)
            if found:
                return found
        return None

    manager_node = _find(tree, manager["id"])
    assert manager_node is not None
    assert any(r["id"] == report["id"] for r in manager_node["reports"])


def test_org_chart_requires_admin(staff_client):
    resp = staff_client.get("/users/org-chart")
    assert resp.status_code == 403


# --- Department heads -------------------------------------------------------


def test_create_department_with_head(admin_client):
    head = _create_user(admin_client, position="partner")
    resp = admin_client.post(
        "/departments/",
        json={"name": f"Audit-{uuid.uuid4().hex[:6]}", "department_head_user_id": head["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["department_head_user_id"] == head["id"]


def test_create_department_with_nonexistent_head_rejected(admin_client):
    resp = admin_client.post(
        "/departments/",
        json={"name": f"Tax-{uuid.uuid4().hex[:6]}", "department_head_user_id": 999999},
    )
    assert resp.status_code == 400


def test_department_detail_groups_staff_by_position(admin_client):
    dept = admin_client.post("/departments/", json={"name": f"Advisory-{uuid.uuid4().hex[:6]}"}).json()
    head = _create_user(admin_client, position="partner", department_id=dept["id"])
    admin_client.put(f"/departments/{dept['id']}", json={"department_head_user_id": head["id"]})
    _create_user(admin_client, position="associate", department_id=dept["id"])
    _create_user(admin_client, position="associate", department_id=dept["id"])

    resp = admin_client.get(f"/departments/{dept['id']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["department_head"]["id"] == head["id"]
    assert body["staff_count"] == 3
    assert len(body["staff_by_position"]["associate"]) == 2


def test_department_detail_404_for_missing_department(admin_client):
    resp = admin_client.get("/departments/999999")
    assert resp.status_code == 404


def test_update_department_head(admin_client):
    dept = admin_client.post("/departments/", json={"name": f"Systems-{uuid.uuid4().hex[:6]}"}).json()
    head = _create_user(admin_client, position="director")

    resp = admin_client.put(f"/departments/{dept['id']}", json={"department_head_user_id": head["id"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["department_head_user_id"] == head["id"]
