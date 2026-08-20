from app.db.session import SessionLocal
from app.models.client_portal_user import ClientPortalUser
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_new_features import _create_client


def _invite_portal_user(admin_client, client_id, **overrides):
    payload = {"name": "Jamie CFO", "email": "jamie@clientco.example.com"}
    payload.update(overrides)
    resp = admin_client.post(f"/clients/{client_id}/portal-users", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_reset_token(email: str) -> str:
    """Portal invite/reset emails aren't actually delivered in tests (see
    app.core.email) -- the token is read straight off the row, same as the
    staff-auth reset flow would need to."""
    with SessionLocal() as db:
        portal_user = db.query(ClientPortalUser).filter(ClientPortalUser.email == email).first()
        assert portal_user is not None
        assert portal_user.reset_token is not None
        return portal_user.reset_token


def _activate_portal_user(client, email: str, password: str = "ClientPass123!"):
    token = _get_reset_token(email)
    resp = client.post("/portal/auth/reset-password", json={"token": token, "new_password": password})
    assert resp.status_code == 200, resp.text
    return password


# --- Invite / manage (staff side) ------------------------------------------


def test_admin_can_invite_portal_user(admin_client):
    client = _create_client(admin_client, email="portal-invite@example.com")
    portal_user = _invite_portal_user(admin_client, client["id"])

    assert portal_user["client_id"] == client["id"]
    assert portal_user["email"] == "jamie@clientco.example.com"
    assert portal_user["disabled"] is False
    assert portal_user["invited_by_email"] == ADMIN_EMAIL


def test_invite_rejects_duplicate_email(admin_client):
    client = _create_client(admin_client, email="portal-dup@example.com")
    _invite_portal_user(admin_client, client["id"], email="dup@clientco.example.com")

    resp = admin_client.post(
        f"/clients/{client['id']}/portal-users", json={"name": "Someone Else", "email": "dup@clientco.example.com"}
    )
    assert resp.status_code == 400


def test_list_portal_users_for_client(admin_client):
    client = _create_client(admin_client, email="portal-list@example.com")
    _invite_portal_user(admin_client, client["id"], email="one@clientco.example.com")
    _invite_portal_user(admin_client, client["id"], email="two@clientco.example.com")

    resp = admin_client.get(f"/clients/{client['id']}/portal-users")
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert emails == {"one@clientco.example.com", "two@clientco.example.com"}


def test_admin_can_disable_portal_user(admin_client):
    client = _create_client(admin_client, email="portal-disable@example.com")
    portal_user = _invite_portal_user(admin_client, client["id"], email="disable@clientco.example.com")

    resp = admin_client.put(
        f"/clients/{client['id']}/portal-users/{portal_user['id']}", json={"disabled": True}
    )
    assert resp.status_code == 200
    assert resp.json()["disabled"] is True


def test_admin_can_revoke_portal_user(admin_client):
    client = _create_client(admin_client, email="portal-revoke@example.com")
    portal_user = _invite_portal_user(admin_client, client["id"], email="revoke@clientco.example.com")

    resp = admin_client.delete(f"/clients/{client['id']}/portal-users/{portal_user['id']}")
    assert resp.status_code == 200

    listing = admin_client.get(f"/clients/{client['id']}/portal-users")
    assert listing.json() == []


def test_invite_unknown_client_404s(admin_client):
    resp = admin_client.post("/clients/999999/portal-users", json={"name": "X", "email": "x@example.com"})
    assert resp.status_code == 404


# --- Portal auth: activation, login, logout, me -----------------------------


def test_portal_user_cannot_login_before_activation(admin_client, client):
    org_client = _create_client(admin_client, email="portal-preactivate@example.com")
    _invite_portal_user(admin_client, org_client["id"], email="preactivate@clientco.example.com")

    resp = client.post(
        "/portal/auth/login",
        data={"username": "preactivate@clientco.example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_portal_user_can_activate_and_login(admin_client, client):
    org_client = _create_client(admin_client, email="portal-activate@example.com")
    _invite_portal_user(admin_client, org_client["id"], email="activate@clientco.example.com")

    password = _activate_portal_user(client, "activate@clientco.example.com")

    resp = client.post(
        "/portal/auth/login",
        data={"username": "activate@clientco.example.com", "password": password},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["token_type"] == "bearer"

    me = client.get("/portal/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "activate@clientco.example.com"
    assert me.json()["client_id"] == org_client["id"]


def test_portal_login_rejects_disabled_account(admin_client, client):
    org_client = _create_client(admin_client, email="portal-disabled-login@example.com")
    portal_user = _invite_portal_user(admin_client, org_client["id"], email="disabledlogin@clientco.example.com")
    password = _activate_portal_user(client, "disabledlogin@clientco.example.com")

    admin_client.put(
        f"/clients/{org_client['id']}/portal-users/{portal_user['id']}", json={"disabled": True}
    )

    resp = client.post(
        "/portal/auth/login",
        data={"username": "disabledlogin@clientco.example.com", "password": password},
    )
    assert resp.status_code == 403


def test_portal_logout_clears_session(admin_client, client):
    org_client = _create_client(admin_client, email="portal-logout@example.com")
    _invite_portal_user(admin_client, org_client["id"], email="logout@clientco.example.com")
    password = _activate_portal_user(client, "logout@clientco.example.com")
    client.post("/portal/auth/login", data={"username": "logout@clientco.example.com", "password": password})

    resp = client.post("/portal/auth/logout")
    assert resp.status_code == 200

    me = client.get("/portal/auth/me")
    assert me.status_code == 401


def test_portal_forgot_password_flow(admin_client, client):
    org_client = _create_client(admin_client, email="portal-forgot@example.com")
    _invite_portal_user(admin_client, org_client["id"], email="forgot@clientco.example.com")
    _activate_portal_user(client, "forgot@clientco.example.com", password="OldPass123!")

    resp = client.post("/portal/auth/request-password-reset", json={"email": "forgot@clientco.example.com"})
    assert resp.status_code == 200

    new_password = _activate_portal_user(client, "forgot@clientco.example.com", password="NewPass456!")

    login = client.post(
        "/portal/auth/login", data={"username": "forgot@clientco.example.com", "password": new_password}
    )
    assert login.status_code == 200


# --- Cross-auth isolation ----------------------------------------------------


def test_staff_token_cannot_authenticate_portal_routes(admin_client):
    """A staff JWT (even passed explicitly as a bearer token, not just via
    the staff-only cookie name) must never authenticate portal routes."""
    login = admin_client.post(
        "/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    staff_token = login.json()["access_token"]

    resp = admin_client.get("/portal/auth/me", headers={"Authorization": f"Bearer {staff_token}"})
    assert resp.status_code == 401


def test_portal_token_cannot_authenticate_staff_routes(admin_client, client):
    org_client = _create_client(admin_client, email="portal-isolation@example.com")
    _invite_portal_user(admin_client, org_client["id"], email="isolation@clientco.example.com")
    password = _activate_portal_user(client, "isolation@clientco.example.com")
    login = client.post(
        "/portal/auth/login", data={"username": "isolation@clientco.example.com", "password": password}
    )
    portal_token = login.json()["access_token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {portal_token}"})
    assert resp.status_code == 401
