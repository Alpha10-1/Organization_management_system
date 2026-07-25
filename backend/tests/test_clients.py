def _create_client(admin_client, **overrides):
    payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "phone": "555-0100",
        "status": "Active",
    }
    payload.update(overrides)
    resp = admin_client.post("/clients/", json=payload)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def test_create_and_fetch_client(admin_client):
    created = _create_client(admin_client, email="fetch-me@example.com")
    resp = admin_client.get(f"/clients/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "fetch-me@example.com"


def test_deleted_client_is_excluded_from_list(admin_client):
    created = _create_client(admin_client, email="list-me@example.com")

    before = admin_client.get("/clients/").json()
    assert any(c["id"] == created["id"] for c in before)

    del_resp = admin_client.delete(f"/clients/{created['id']}")
    assert del_resp.status_code == 200

    after = admin_client.get("/clients/").json()
    assert all(c["id"] != created["id"] for c in after)


def test_deleted_client_404s_on_direct_fetch(admin_client):
    created = _create_client(admin_client, email="soon-deleted@example.com")
    admin_client.delete(f"/clients/{created['id']}")

    resp = admin_client.get(f"/clients/{created['id']}")
    assert resp.status_code == 404


def test_deleting_already_deleted_client_404s(admin_client):
    created = _create_client(admin_client, email="double-delete@example.com")
    first = admin_client.delete(f"/clients/{created['id']}")
    assert first.status_code == 200

    second = admin_client.delete(f"/clients/{created['id']}")
    assert second.status_code == 404


def test_deleted_client_row_is_kept_for_soft_delete_not_removed(admin_client):
    """The whole point of soft delete: the row survives with deleted_at
    set, rather than being physically removed from the table."""
    from app.db.session import SessionLocal
    from app.models.client import Client

    created = _create_client(admin_client, email="kept-for-audit@example.com")
    admin_client.delete(f"/clients/{created['id']}")

    with SessionLocal() as db:
        row = db.query(Client).filter(Client.id == created["id"]).first()
        assert row is not None
        assert row.deleted_at is not None
