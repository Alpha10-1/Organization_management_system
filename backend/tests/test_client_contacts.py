from tests.test_new_features import _create_client


# --- Contacts --------------------------------------------------------------


def test_add_and_list_client_contact(admin_client):
    client = _create_client(admin_client, email="contact-client@example.com")

    resp = admin_client.post(
        f"/clients/{client['id']}/contacts",
        json={"name": "Sam CFO", "role": "CFO", "email": "sam@acme.com", "is_primary": True},
    )
    assert resp.status_code == 200, resp.text
    contact = resp.json()
    assert contact["name"] == "Sam CFO"
    assert contact["is_primary"] is True

    listed = admin_client.get(f"/clients/{client['id']}/contacts").json()
    assert len(listed) == 1
    assert listed[0]["id"] == contact["id"]


def test_only_one_primary_contact_per_client(admin_client):
    client = _create_client(admin_client, email="primary-swap@example.com")

    first = admin_client.post(
        f"/clients/{client['id']}/contacts",
        json={"name": "First Contact", "is_primary": True},
    ).json()

    second = admin_client.post(
        f"/clients/{client['id']}/contacts",
        json={"name": "Second Contact", "is_primary": True},
    ).json()

    listed = {c["id"]: c for c in admin_client.get(f"/clients/{client['id']}/contacts").json()}
    assert listed[first["id"]]["is_primary"] is False
    assert listed[second["id"]]["is_primary"] is True


def test_update_and_delete_client_contact(admin_client):
    client = _create_client(admin_client, email="update-contact@example.com")
    contact = admin_client.post(
        f"/clients/{client['id']}/contacts", json={"name": "Original Name"}
    ).json()

    resp = admin_client.put(
        f"/clients/{client['id']}/contacts/{contact['id']}", json={"name": "Updated Name"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Updated Name"

    resp = admin_client.delete(f"/clients/{client['id']}/contacts/{contact['id']}")
    assert resp.status_code == 200, resp.text

    listed = admin_client.get(f"/clients/{client['id']}/contacts").json()
    assert all(c["id"] != contact["id"] for c in listed)


def test_contact_requires_existing_client(admin_client):
    resp = admin_client.post("/clients/999999/contacts", json={"name": "Ghost"})
    assert resp.status_code == 404


# --- Hierarchy ---------------------------------------------------------


def test_client_can_reference_parent_client(admin_client):
    parent = _create_client(admin_client, email="parent-co@example.com", first_name="Parent", last_name="Co")
    child = _create_client(
        admin_client,
        email="subsidiary@example.com",
        first_name="Subsidiary",
        last_name="Co",
        parent_client_id=parent["id"],
    )
    assert child["parent_client_id"] == parent["id"]


def test_client_rejects_unknown_parent(admin_client):
    resp = admin_client.post(
        "/clients/",
        json={
            "first_name": "Orphan",
            "last_name": "Co",
            "email": "orphan@example.com",
            "parent_client_id": 999999,
        },
    )
    assert resp.status_code == 404


def test_client_cannot_be_its_own_parent(admin_client):
    client = _create_client(admin_client, email="self-parent@example.com")
    resp = admin_client.put(f"/clients/{client['id']}", json={"parent_client_id": client["id"]})
    assert resp.status_code == 400


# --- Relationship health -------------------------------------------------


def test_client_health_defaults_to_green_with_no_signals(admin_client):
    client = _create_client(admin_client, email="healthy@example.com")
    resp = admin_client.get(f"/clients/{client['id']}/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["health"] == "green"
    assert body["is_manual_override"] is False
    assert body["overdue_task_count"] == 0


def test_client_health_turns_amber_with_overdue_task(admin_client):
    client = _create_client(admin_client, email="amber-client@example.com")
    admin_client.post(
        "/tasks/",
        json={"title": "Overdue item", "client_id": client["id"], "due_date": "2020-01-01T00:00:00"},
    )

    body = admin_client.get(f"/clients/{client['id']}/health").json()
    assert body["health"] == "amber"
    assert body["overdue_task_count"] == 1


def test_client_health_manual_override(admin_client):
    client = _create_client(admin_client, email="override-client@example.com")

    resp = admin_client.put(f"/clients/{client['id']}", json={"relationship_health": "red"})
    assert resp.status_code == 200, resp.text

    body = admin_client.get(f"/clients/{client['id']}/health").json()
    assert body["health"] == "red"
    assert body["is_manual_override"] is True
    assert body["computed_health"] == "green"


def test_client_health_rejects_invalid_value(admin_client):
    client = _create_client(admin_client, email="bad-health@example.com")
    resp = admin_client.put(f"/clients/{client['id']}", json={"relationship_health": "purple"})
    assert resp.status_code == 400
