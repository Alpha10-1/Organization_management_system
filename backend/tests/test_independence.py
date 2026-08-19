import uuid

from tests.conftest import ADMIN_EMAIL, STAFF_EMAIL
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _create_user(admin_client, **overrides):
    payload = {
        "name": "Conflict Test User",
        "email": _unique_email("conflict"),
        "password": "Sup3rSecret!",
        "role": "staff",
    }
    payload.update(overrides)
    resp = admin_client.post("/users/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_disclosure(admin_client, user_id, client_id=None, **overrides):
    payload = {
        "user_id": user_id,
        "client_id": client_id,
        "disclosure_type": "financial_interest",
        "description": "Holds shares in the client's parent company.",
    }
    payload.update(overrides)
    resp = admin_client.post("/independence/disclosures", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Disclosure CRUD --------------------------------------------------------


def test_admin_can_create_disclosure_for_staff(admin_client):
    user = _create_user(admin_client)
    disclosure = _create_disclosure(admin_client, user["id"])
    assert disclosure["user_id"] == user["id"]
    assert disclosure["status"] == "active"
    assert disclosure["disclosure_type"] == "financial_interest"


def test_staff_can_create_own_disclosure(staff_client):
    resp = staff_client.post(
        "/independence/disclosures",
        json={
            "disclosure_type": "family_relationship",
            "description": "Spouse is employed by the client.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_by_email"] == STAFF_EMAIL


def test_staff_cannot_create_disclosure_for_someone_else(staff_client, admin_client):
    other = _create_user(admin_client)
    resp = staff_client.post(
        "/independence/disclosures",
        json={
            "user_id": other["id"],
            "disclosure_type": "other",
            "description": "Some other conflict.",
        },
    )
    assert resp.status_code == 403


def test_invalid_disclosure_type_rejected(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.post(
        "/independence/disclosures",
        json={"user_id": user["id"], "disclosure_type": "bribery", "description": "x"},
    )
    assert resp.status_code == 400


def test_staff_only_sees_own_disclosures(staff_client, admin_client):
    other = _create_user(admin_client)
    _create_disclosure(admin_client, other["id"])

    resp = staff_client.get("/independence/disclosures")
    assert resp.status_code == 200
    assert all(d["user_id"] != other["id"] for d in resp.json())


def test_admin_sees_all_disclosures_filtered_by_user(admin_client):
    user = _create_user(admin_client)
    _create_disclosure(admin_client, user["id"])

    resp = admin_client.get("/independence/disclosures", params={"user_id": user["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert all(d["user_id"] == user["id"] for d in body)


def test_resolve_disclosure_sets_resolved_metadata(admin_client):
    user = _create_user(admin_client)
    disclosure = _create_disclosure(admin_client, user["id"])

    resp = admin_client.put(f"/independence/disclosures/{disclosure['id']}", json={"status": "resolved"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None
    assert body["resolved_by_email"] == ADMIN_EMAIL


def test_owner_can_resolve_own_disclosure(staff_client):
    created = staff_client.post(
        "/independence/disclosures",
        json={"disclosure_type": "other", "description": "Prior consulting engagement."},
    ).json()

    resp = staff_client.put(f"/independence/disclosures/{created['id']}", json={"status": "resolved"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "resolved"


def test_non_owner_staff_cannot_update_disclosure(staff_client, admin_client):
    other = _create_user(admin_client)
    disclosure = _create_disclosure(admin_client, other["id"])

    resp = staff_client.put(f"/independence/disclosures/{disclosure['id']}", json={"status": "resolved"})
    assert resp.status_code == 403


def test_delete_disclosure_soft_deletes(admin_client):
    user = _create_user(admin_client)
    disclosure = _create_disclosure(admin_client, user["id"])

    resp = admin_client.delete(f"/independence/disclosures/{disclosure['id']}")
    assert resp.status_code == 200, resp.text

    listed = admin_client.get("/independence/disclosures", params={"user_id": user["id"]}).json()
    assert all(d["id"] != disclosure["id"] for d in listed)


# --- Conflict check ----------------------------------------------------------


def test_conflict_check_returns_empty_when_no_disclosures(admin_client):
    user = _create_user(admin_client)
    conflict_client = _create_client(admin_client, email=_unique_email("client"))

    resp = admin_client.get(
        "/independence/check", params={"user_id": user["id"], "client_id": conflict_client["id"]}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_conflict"] is False
    assert body["disclosures"] == []


def test_conflict_check_flags_active_disclosure_against_client(admin_client):
    user = _create_user(admin_client)
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    resp = admin_client.get(
        "/independence/check", params={"user_id": user["id"], "client_id": conflict_client["id"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_conflict"] is True
    assert len(body["disclosures"]) == 1


def test_conflict_check_ignores_resolved_disclosure(admin_client):
    user = _create_user(admin_client)
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    disclosure = _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])
    admin_client.put(f"/independence/disclosures/{disclosure['id']}", json={"status": "resolved"})

    resp = admin_client.get(
        "/independence/check", params={"user_id": user["id"], "client_id": conflict_client["id"]}
    )
    assert resp.json()["has_conflict"] is False


def test_conflict_check_ignores_disclosure_for_unrelated_client(admin_client):
    user = _create_user(admin_client)
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    unrelated_client = _create_client(admin_client, email=_unique_email("client"))
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    resp = admin_client.get(
        "/independence/check", params={"user_id": user["id"], "client_id": unrelated_client["id"]}
    )
    assert resp.json()["has_conflict"] is False


def test_conflict_check_ignores_general_disclosure_without_client(admin_client):
    """A disclosure with no client_id is firm-wide/general and must never
    auto-flag every engagement -- see app.core.independence docstring."""
    user = _create_user(admin_client)
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    _create_disclosure(admin_client, user["id"], client_id=None)

    resp = admin_client.get(
        "/independence/check", params={"user_id": user["id"], "client_id": conflict_client["id"]}
    )
    assert resp.json()["has_conflict"] is False


def test_conflict_check_matches_against_parent_client_in_group(admin_client):
    parent = _create_client(admin_client, email=_unique_email("parent"), client_type="business", company_name="Parent Holdco")
    subsidiary = _create_client(
        admin_client,
        email=_unique_email("sub"),
        client_type="business",
        company_name="Subsidiary Ops",
        parent_client_id=parent["id"],
    )
    user = _create_user(admin_client)
    _create_disclosure(admin_client, user["id"], client_id=parent["id"])

    resp = admin_client.get(
        "/independence/check", params={"user_id": user["id"], "client_id": subsidiary["id"]}
    )
    assert resp.status_code == 200
    assert resp.json()["has_conflict"] is True


# --- Staffing integration ----------------------------------------------------


def test_assignment_blocked_when_active_conflict_exists(admin_client):
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client)
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    resp = admin_client.post(f"/projects/{project['id']}/assignments", json={"user_id": user["id"]})
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["conflicts"]

    # And no assignment was actually created.
    listed = admin_client.get(f"/projects/{project['id']}/assignments").json()
    assert all(a["user_id"] != user["id"] for a in listed)


def test_assignment_allowed_when_no_conflict(admin_client):
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client)

    resp = admin_client.post(f"/projects/{project['id']}/assignments", json={"user_id": user["id"]})
    assert resp.status_code == 200, resp.text


def test_admin_can_override_conflict_with_reason(admin_client):
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client)
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": user["id"], "conflict_override_reason": "Safeguard: second partner will review all work."},
    )
    assert resp.status_code == 200, resp.text

    overrides = admin_client.get("/independence/overrides", params={"project_id": project["id"]}).json()
    assert len(overrides) == 1
    assert overrides[0]["user_id"] == user["id"]
    assert overrides[0]["reason"].startswith("Safeguard")


def test_staff_cannot_override_conflict(staff_client, admin_client):
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client)
    _create_disclosure(admin_client, user["id"], client_id=conflict_client["id"])

    resp = staff_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": user["id"], "conflict_override_reason": "I say it's fine."},
    )
    assert resp.status_code == 403


def test_standalone_override_endpoint_requires_existing_conflict(admin_client):
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, conflict_client["id"])
    user = _create_user(admin_client)

    resp = admin_client.post(
        "/independence/overrides",
        json={"project_id": project["id"], "user_id": user["id"], "reason": "no conflict exists"},
    )
    assert resp.status_code == 400


def test_department_assignment_not_subject_to_conflict_check(admin_client):
    """Conflicts are checked per-individual; staffing a whole department
    has no single person to check against, so it should never be blocked
    by this mechanism."""
    conflict_client = _create_client(admin_client, email=_unique_email("client"))
    project = _create_project(admin_client, conflict_client["id"])
    dept = admin_client.post("/departments/", json={"name": f"Dept-{uuid.uuid4().hex[:6]}"}).json()

    resp = admin_client.post(f"/projects/{project['id']}/assignments", json={"department_id": dept["id"]})
    assert resp.status_code == 200, resp.text
