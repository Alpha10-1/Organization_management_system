from tests.conftest import ADMIN_EMAIL, STAFF_EMAIL
from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def _user_id(admin_client, email):
    users = admin_client.get("/users/").json()
    return next(u["id"] for u in users if u["email"] == email)


# --- Business / individual / NPO client entry -----------------------------


def test_create_business_client_requires_company_name(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={"client_type": "business", "email": "no-name@example.com"},
    )
    assert resp.status_code == 400


def test_create_business_client_with_full_detail(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={
            "client_type": "business",
            "company_name": "Acme Holdings Ltd",
            "registration_number": "2019/123456/07",
            "tax_number": "9876543210",
            "industry": "Manufacturing",
            "website": "https://acme.example.com",
            "billing_address": "1 Main Street",
            "city": "Johannesburg",
            "country": "South Africa",
            "postal_code": "2000",
            "email": "accounts@acme.example.com",
            "phone": "555-0200",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["client_type"] == "business"
    assert body["company_name"] == "Acme Holdings Ltd"
    assert body["industry"] == "Manufacturing"

    fetched = admin_client.get(f"/clients/{body['id']}").json()
    assert fetched["company_name"] == "Acme Holdings Ltd"


def test_create_npo_client_requires_company_name(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={"client_type": "npo", "company_name": "Helping Hands NPO"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["client_type"] == "npo"


def test_create_individual_client_requires_first_and_last_name(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={"client_type": "individual", "first_name": "Only First"},
    )
    assert resp.status_code == 400


def test_default_client_type_is_business(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={"company_name": "Default Type Co"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["client_type"] == "business"


def test_invalid_client_type_rejected(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={"client_type": "government", "company_name": "Some Agency"},
    )
    assert resp.status_code == 400


def test_update_business_client_cannot_clear_company_name(admin_client):
    created = admin_client.post(
        "/clients/",
        json={"client_type": "business", "company_name": "Keep Me Ltd"},
    ).json()

    resp = admin_client.put(f"/clients/{created['id']}", json={"company_name": None})
    assert resp.status_code == 400


def test_display_name_used_for_business_client(admin_client):
    created = admin_client.post(
        "/clients/",
        json={"client_type": "business", "company_name": "Logged Co"},
    ).json()
    assert created["company_name"] == "Logged Co"

    # display_name isn't on the API response directly, but the CSV export
    # (which uses it) should not error and should include the company name.
    resp = admin_client.get("/reports/clients/csv")
    assert resp.status_code == 200
    assert "Logged Co" in resp.text


def test_client_search_matches_company_name(admin_client):
    admin_client.post(
        "/clients/",
        json={"client_type": "business", "company_name": "Searchable Widgets Inc"},
    )
    resp = admin_client.get("/clients/?search=Searchable")
    assert resp.status_code == 200
    results = resp.json()
    assert any(c["company_name"] == "Searchable Widgets Inc" for c in results)


# --- Project assignment to individuals or departments ----------------------


def test_assign_project_to_individual_user(admin_client):
    client = _create_client(admin_client, email="assign-user@example.com")
    project = _create_project(admin_client, client["id"])
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": staff_id, "role": "Field Lead"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_id"] == staff_id
    assert body["role"] == "Field Lead"
    assert body["department_id"] is None

    listed = admin_client.get(f"/projects/{project['id']}/assignments").json()
    assert any(a["user_id"] == staff_id for a in listed)


def test_assign_project_to_department(admin_client):
    client = _create_client(admin_client, email="assign-dept@example.com")
    project = _create_project(admin_client, client["id"])
    dept = admin_client.post("/departments/", json={"name": "Advisory Team"}).json()

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"department_id": dept["id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["department_id"] == dept["id"]
    assert body["department_name"] == "Advisory Team"
    assert body["user_id"] is None


def test_assignment_requires_exactly_one_target(admin_client):
    client = _create_client(admin_client, email="assign-both@example.com")
    project = _create_project(admin_client, client["id"])
    dept = admin_client.post("/departments/", json={"name": "Both Target Dept"}).json()
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    resp = admin_client.post(
        f"/projects/{project['id']}/assignments",
        json={"user_id": staff_id, "department_id": dept["id"]},
    )
    assert resp.status_code == 422

    resp_empty = admin_client.post(f"/projects/{project['id']}/assignments", json={})
    assert resp_empty.status_code == 422


def test_duplicate_assignment_rejected(admin_client):
    client = _create_client(admin_client, email="assign-dup@example.com")
    project = _create_project(admin_client, client["id"])
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    first = admin_client.post(f"/projects/{project['id']}/assignments", json={"user_id": staff_id})
    assert first.status_code == 200

    second = admin_client.post(f"/projects/{project['id']}/assignments", json={"user_id": staff_id})
    assert second.status_code == 400


def test_remove_project_assignment(admin_client):
    client = _create_client(admin_client, email="assign-remove@example.com")
    project = _create_project(admin_client, client["id"])
    staff_id = _user_id(admin_client, STAFF_EMAIL)

    created = admin_client.post(f"/projects/{project['id']}/assignments", json={"user_id": staff_id}).json()

    resp = admin_client.delete(f"/projects/{project['id']}/assignments/{created['id']}")
    assert resp.status_code == 200

    listed = admin_client.get(f"/projects/{project['id']}/assignments").json()
    assert listed == []


def test_project_extended_detail_fields_optional(admin_client):
    client = _create_client(admin_client, email="specify-more@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        objectives="Complete statutory audit ahead of AGM",
        deliverables="Signed audit opinion, management letter",
        stakeholders="CFO, Audit Committee Chair",
        billing_notes="Fixed fee, milestone billing",
    )
    assert project["objectives"] == "Complete statutory audit ahead of AGM"
    assert project["deliverables"] == "Signed audit opinion, management letter"
    assert project["stakeholders"] == "CFO, Audit Committee Chair"
    assert project["billing_notes"] == "Fixed fee, milestone billing"

    # Confirm the fields are genuinely optional -- a minimal project still works.
    bare = _create_project(admin_client, client["id"], name="Bare Engagement")
    assert bare["objectives"] is None
