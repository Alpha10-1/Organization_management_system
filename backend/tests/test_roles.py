import uuid

from tests.conftest import ADMIN_EMAIL
from tests.test_independence import _create_disclosure
from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_staffing import _create_user
from tests.test_workpapers import _create_workpaper, _setup_project

ROLES_URL = "/roles"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_custom_role(admin_client, **overrides):
    payload = {"name": _unique("Custom Role"), "description": "A test role", "permissions": []}
    payload.update(overrides)
    resp = admin_client.post(f"{ROLES_URL}/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_delegated_user(admin_client, client, permissions, **overrides):
    """Creates a plain staff user, a fresh custom role granting exactly
    `permissions`, assigns it, and logs the user in on the given
    unauthenticated `client` fixture. Returns (user, logged_in_headers)."""
    user = _create_user(admin_client, email=_unique("delegate") + "@example.com", **overrides)
    role = _create_custom_role(admin_client, permissions=permissions)
    resp = admin_client.patch(f"/users/{user['email']}/custom-role", json={"custom_role_id": role["id"]})
    assert resp.status_code == 200, resp.text

    login = client.post("/auth/login", data={"username": user["email"], "password": "Sup3rSecret!"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user, role, headers


# --- permission catalog ------------------------------------------------------


def test_catalog_lists_known_permissions(admin_client):
    resp = admin_client.get(f"{ROLES_URL}/catalog")
    assert resp.status_code == 200, resp.text
    catalog = resp.json()
    assert "leave.approve_any" in catalog
    assert "independence.override" in catalog
    assert "workpapers.override" in catalog


def test_catalog_requires_admin(staff_client):
    resp = staff_client.get(f"{ROLES_URL}/catalog")
    assert resp.status_code == 403


# --- seeded system roles -----------------------------------------------------


def test_default_system_roles_seeded(admin_client):
    resp = admin_client.get(f"{ROLES_URL}/")
    assert resp.status_code == 200, resp.text
    names = {r["name"] for r in resp.json()}
    assert {"Partner", "Manager", "Engagement Quality Reviewer"}.issubset(names)
    partner = next(r for r in resp.json() if r["name"] == "Partner")
    assert partner["is_system"] is True


# --- role CRUD ----------------------------------------------------------------


def test_create_custom_role(admin_client):
    role = _create_custom_role(admin_client, permissions=["tags.manage"])
    assert role["permissions"] == ["tags.manage"]
    assert role["is_system"] is False


def test_create_role_rejects_unknown_permission(admin_client):
    resp = admin_client.post(
        f"{ROLES_URL}/", json={"name": _unique("Bad Role"), "permissions": ["nonsense.permission"]}
    )
    assert resp.status_code == 400


def test_create_role_rejects_duplicate_name(admin_client):
    name = _unique("Dup Role")
    admin_client.post(f"{ROLES_URL}/", json={"name": name, "permissions": []})
    resp = admin_client.post(f"{ROLES_URL}/", json={"name": name, "permissions": []})
    assert resp.status_code == 400


def test_update_role_permissions(admin_client):
    role = _create_custom_role(admin_client, permissions=["tags.manage"])
    resp = admin_client.put(f"{ROLES_URL}/{role['id']}", json={"permissions": ["tags.manage", "departments.manage"]})
    assert resp.status_code == 200, resp.text
    assert set(resp.json()["permissions"]) == {"tags.manage", "departments.manage"}


def test_update_system_role_permissions_allowed(admin_client):
    """System roles are protected from deletion, not from customization --
    an admin can freely edit what a seeded role grants."""
    roles = admin_client.get(f"{ROLES_URL}/").json()
    manager_role = next(r for r in roles if r["name"] == "Manager")

    resp = admin_client.put(f"{ROLES_URL}/{manager_role['id']}", json={"permissions": ["tags.manage"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["permissions"] == ["tags.manage"]

    # restore so other tests relying on the seeded Manager permission set aren't affected
    admin_client.put(f"{ROLES_URL}/{manager_role['id']}", json={"permissions": manager_role["permissions"]})


def test_update_role_rejects_unknown_permission(admin_client):
    role = _create_custom_role(admin_client)
    resp = admin_client.put(f"{ROLES_URL}/{role['id']}", json={"permissions": ["not.a.real.permission"]})
    assert resp.status_code == 400


def test_delete_custom_role(admin_client):
    role = _create_custom_role(admin_client)
    resp = admin_client.delete(f"{ROLES_URL}/{role['id']}")
    assert resp.status_code == 200
    assert admin_client.get(f"{ROLES_URL}/{role['id']}").status_code == 404


def test_delete_system_role_rejected(admin_client):
    roles = admin_client.get(f"{ROLES_URL}/").json()
    partner_role = next(r for r in roles if r["name"] == "Partner")
    resp = admin_client.delete(f"{ROLES_URL}/{partner_role['id']}")
    assert resp.status_code == 400


def test_delete_role_with_assigned_users_rejected(admin_client):
    role = _create_custom_role(admin_client)
    user = _create_user(admin_client, email=_unique("assigned") + "@example.com")
    admin_client.patch(f"/users/{user['email']}/custom-role", json={"custom_role_id": role["id"]})

    resp = admin_client.delete(f"{ROLES_URL}/{role['id']}")
    assert resp.status_code == 400


def test_role_endpoints_require_admin(staff_client):
    assert staff_client.get(f"{ROLES_URL}/").status_code == 403
    assert staff_client.post(f"{ROLES_URL}/", json={"name": "x", "permissions": []}).status_code == 403


# --- assigning custom roles ---------------------------------------------------


def test_admin_can_assign_and_clear_custom_role(admin_client):
    role = _create_custom_role(admin_client)
    user = _create_user(admin_client, email=_unique("assignee") + "@example.com")

    resp = admin_client.patch(f"/users/{user['email']}/custom-role", json={"custom_role_id": role["id"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["custom_role_id"] == role["id"]

    resp = admin_client.patch(f"/users/{user['email']}/custom-role", json={"custom_role_id": None})
    assert resp.status_code == 200, resp.text
    assert resp.json()["custom_role_id"] is None


def test_assign_unknown_role_404(admin_client):
    user = _create_user(admin_client, email=_unique("assignee2") + "@example.com")
    resp = admin_client.patch(f"/users/{user['email']}/custom-role", json={"custom_role_id": 999999})
    assert resp.status_code == 404


def test_staff_cannot_assign_custom_roles(staff_client, admin_client):
    role = _create_custom_role(admin_client)
    user = _create_user(admin_client, email=_unique("assignee3") + "@example.com")
    resp = staff_client.patch(f"/users/{user['email']}/custom-role", json={"custom_role_id": role["id"]})
    assert resp.status_code == 403


# --- delegated permission enforcement: baseline (no permission => 403) ------


def test_plain_staff_without_role_cannot_view_users(client):
    resp = client.get("/users/")
    assert resp.status_code == 401  # unauthenticated entirely, sanity check on the route


def test_staff_without_custom_role_cannot_manage_departments(staff_client):
    resp = staff_client.post("/departments/", json={"name": _unique("Dept")})
    assert resp.status_code == 403


# --- delegated permission enforcement: users.view / users.manage -----------


def test_delegated_users_view_permission_allows_listing(admin_client, client):
    _, _, headers = _create_delegated_user(admin_client, client, ["users.view"])
    resp = client.get("/users/", headers=headers)
    assert resp.status_code == 200, resp.text


def test_delegated_users_manage_permission_allows_creating_staff(admin_client, client):
    _, _, headers = _create_delegated_user(admin_client, client, ["users.manage"])
    resp = client.post(
        "/users/",
        json={"name": "New Hire", "email": _unique("newhire") + "@example.com", "password": "Sup3rSecret!", "role": "staff"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_delegated_users_manage_permission_cannot_create_admin(admin_client, client):
    _, _, headers = _create_delegated_user(admin_client, client, ["users.manage"])
    resp = client.post(
        "/users/",
        json={"name": "Sneaky Admin", "email": _unique("sneaky") + "@example.com", "password": "Sup3rSecret!", "role": "admin"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_delegated_permission_never_allows_role_change(admin_client, client):
    """Even a user with every permission in the catalog cannot change
    another user's system role -- that stays hard admin-only."""
    from app.core.permissions import PERMISSION_CATALOG

    target = _create_user(admin_client, email=_unique("roletarget") + "@example.com")
    _, _, headers = _create_delegated_user(admin_client, client, list(PERMISSION_CATALOG.keys()))

    resp = client.patch(f"/users/{target['email']}/role", json={"role": "admin"}, headers=headers)
    assert resp.status_code == 403


def test_delegated_permission_never_allows_role_management(admin_client, client):
    """Even a fully-permissioned delegated user cannot touch /roles/ --
    role/permission management is never itself delegable."""
    from app.core.permissions import PERMISSION_CATALOG

    _, _, headers = _create_delegated_user(admin_client, client, list(PERMISSION_CATALOG.keys()))
    resp = client.get(f"{ROLES_URL}/", headers=headers)
    assert resp.status_code == 403


# --- delegated permission enforcement: departments/tags ---------------------


def test_delegated_departments_manage_permission(admin_client, client):
    _, _, headers = _create_delegated_user(admin_client, client, ["departments.manage"])
    resp = client.post("/departments/", json={"name": _unique("Delegated Dept")}, headers=headers)
    assert resp.status_code == 200, resp.text
    dept_id = resp.json()["id"]

    resp = client.delete(f"/departments/{dept_id}", headers=headers)
    assert resp.status_code == 200, resp.text


def test_delegated_tags_manage_permission(admin_client, client):
    tag = admin_client.post("/tags/", json={"name": _unique("DelegatedTag")}).json()
    _, _, headers = _create_delegated_user(admin_client, client, ["tags.manage"])

    resp = client.put(f"/tags/{tag['id']}", json={"color": "#123456"}, headers=headers)
    assert resp.status_code == 200, resp.text

    resp = client.delete(f"/tags/{tag['id']}", headers=headers)
    assert resp.status_code == 200, resp.text


# --- delegated permission enforcement: leave.approve_any --------------------


def test_delegated_leave_approve_any_permission(admin_client, client):
    manager = _create_user(admin_client, email=_unique("leavemgr") + "@example.com", position="manager")
    report = _create_user(admin_client, email=_unique("leaverep") + "@example.com", manager_id=manager["id"])

    login = client.post("/auth/login", data={"username": report["email"], "password": "Sup3rSecret!"})
    token = login.json()["access_token"]
    leave = client.post(
        "/leave-requests/",
        json={"leave_type": "pto", "start_date": "2027-02-01", "end_date": "2027-02-02"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    _, _, headers = _create_delegated_user(admin_client, client, ["leave.approve_any"])
    resp = client.post(f"/leave-requests/{leave['id']}/approve", json={}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"


# --- delegated permission enforcement: independence.override ---------------


def test_delegated_independence_override_permission_on_assignment(admin_client, client):
    conflict_client = _create_client(admin_client, email=_unique("indep-client") + "@example.com")
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client, email=_unique("indep-user") + "@example.com")
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    _, _, headers = _create_delegated_user(admin_client, client, ["independence.override"])
    resp = client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": user["id"], "conflict_override_reason": "EQR pre-approved a safeguard."},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_delegated_independence_override_standalone_endpoint(admin_client, client):
    conflict_client = _create_client(admin_client, email=_unique("indep-client2") + "@example.com")
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client, email=_unique("indep-user2") + "@example.com")
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    _, _, headers = _create_delegated_user(admin_client, client, ["independence.override"])
    resp = client.post(
        "/independence/overrides",
        json={
            "project_id": project["id"],
            "user_id": user["id"],
            "reason": "EQR pre-approved a safeguard.",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_without_permission_independence_override_rejected(admin_client, client):
    conflict_client = _create_client(admin_client, email=_unique("indep-client3") + "@example.com")
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client, email=_unique("indep-user3") + "@example.com")
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    _, _, headers = _create_delegated_user(admin_client, client, ["tags.manage"])
    resp = client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": user["id"], "conflict_override_reason": "Should not be allowed."},
        headers=headers,
    )
    assert resp.status_code == 403


# --- delegated permission enforcement: workpapers.override ------------------


def test_delegated_workpapers_override_permission(admin_client, client):
    project = _setup_project(admin_client)
    reviewer = _create_user(admin_client, email=_unique("wp-reviewer") + "@example.com")
    partner = _create_user(admin_client, email=_unique("wp-partner") + "@example.com", role="admin")
    workpaper = _create_workpaper(
        admin_client, project["id"], reviewer_id=reviewer["id"], partner_id=partner["id"]
    )
    admin_client.put(f"/workpapers/{workpaper['id']}/submit", json={})

    _, _, headers = _create_delegated_user(admin_client, client, ["workpapers.override"])
    resp = client.put(
        f"/workpapers/{workpaper['id']}/review", json={"status": "approved"}, headers=headers
    )
    assert resp.status_code == 200, resp.text


# --- delegated permission enforcement: time_entries.manage_others ----------


def test_delegated_time_entries_manage_others_permission(admin_client, client):
    owner = _create_user(admin_client, email=_unique("te-owner") + "@example.com")
    project_client = _create_client(admin_client, email=_unique("te-client") + "@example.com")
    project = _create_project(admin_client, project_client["id"])

    login = client.post("/auth/login", data={"username": owner["email"], "password": "Sup3rSecret!"})
    token = login.json()["access_token"]
    entry = client.post(
        "/time-entries/",
        json={"project_id": project["id"], "hours": "2.0", "entry_date": "2027-01-05", "billable": True},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    _, _, headers = _create_delegated_user(admin_client, client, ["time_entries.manage_others"])
    resp = client.put(f"/time-entries/{entry['id']}", json={"hours": "3.0"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["hours"]) == 3.0


# --- delegated permission enforcement: content.moderate ---------------------


def test_delegated_content_moderate_permission_on_client_notes(admin_client, client):
    note_client = _create_client(admin_client, email=_unique("note-client") + "@example.com")
    note = admin_client.post(f"/clients/{note_client['id']}/notes", json={"body": "Original note"}).json()

    _, _, headers = _create_delegated_user(admin_client, client, ["content.moderate"])
    resp = client.delete(f"/clients/{note_client['id']}/notes/{note['id']}", headers=headers)
    assert resp.status_code == 200, resp.text


def test_delegated_content_moderate_permission_on_comments(admin_client, client):
    comment = admin_client.post("/comments/", json={"entity_type": "project", "entity_id": 1, "body": "hi"}).json()

    _, _, headers = _create_delegated_user(admin_client, client, ["content.moderate"])
    resp = client.delete(f"/comments/{comment['id']}", headers=headers)
    assert resp.status_code == 200, resp.text


# --- delegated permission enforcement: users.manage_status ------------------


def test_delegated_users_manage_status_permission(admin_client, client):
    target = _create_user(admin_client, email=_unique("statustarget") + "@example.com")
    _, _, headers = _create_delegated_user(admin_client, client, ["users.manage_status"])

    resp = client.patch(f"/users/{target['email']}/status", json={"disabled": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["disabled"] is True
