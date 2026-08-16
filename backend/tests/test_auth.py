from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, STAFF_EMAIL, STAFF_PASSWORD


def test_login_succeeds_with_correct_credentials(client):
    resp = client.post(
        "/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_login_sets_httponly_cookie(client):
    resp = client.post(
        "/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


def test_login_fails_with_wrong_password(client):
    resp = client.post(
        "/auth/login",
        data={"username": ADMIN_EMAIL, "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_fails_for_unknown_user(client):
    resp = client.post(
        "/auth/login",
        data={"username": "nobody@org.com", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_via_cookie(admin_client):
    resp = admin_client.get("/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"


def test_me_works_via_authorization_header_too(client):
    # Backward-compat path for API clients / Swagger that can't rely on
    # browser cookie handling.
    login = client.post(
        "/auth/login",
        data={"username": STAFF_EMAIL, "password": STAFF_PASSWORD},
    )
    token = login.json()["access_token"]

    # A fresh, cookie-less request using only the bearer token.
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == STAFF_EMAIL


def test_logout_clears_cookie_and_ends_session(admin_client):
    assert admin_client.get("/auth/me").status_code == 200

    logout_resp = admin_client.post("/auth/logout")
    assert logout_resp.status_code == 200

    resp = admin_client.get("/auth/me")
    assert resp.status_code == 401


def test_login_rate_limit_blocks_after_repeated_failures(client):
    for _ in range(5):
        resp = client.post(
            "/auth/login",
            data={"username": ADMIN_EMAIL, "password": "wrong-password"},
        )
        assert resp.status_code == 401

    # The 6th attempt (even with the *correct* password) should be blocked
    # by the per-account rate limit, not just fail auth.
    resp = client.post(
        "/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_successful_login_resets_rate_limit_counter(client):
    # A few failures, then a success, should clear the counter so the
    # legitimate user isn't penalized for their own earlier typos.
    for _ in range(3):
        client.post(
            "/auth/login",
            data={"username": STAFF_EMAIL, "password": "wrong-password"},
        )

    ok = client.post(
        "/auth/login",
        data={"username": STAFF_EMAIL, "password": STAFF_PASSWORD},
    )
    assert ok.status_code == 200

    # Should be able to fail a couple more times without hitting the
    # 5-attempt window immediately, since the counter was reset.
    resp = client.post(
        "/auth/login",
        data={"username": STAFF_EMAIL, "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_admin_and_staff_clients_stay_independent(admin_client, staff_client):
    """Regression test: admin_client and staff_client used to share a
    single TestClient/cookie jar, so requesting both in one test left only
    the second login's session active (auth bleed-through). Each fixture
    now gets its own independent client, so both sessions must remain
    valid and correctly scoped for the lifetime of the test."""
    admin_me = admin_client.get("/auth/me")
    staff_me = staff_client.get("/auth/me")
    assert admin_me.status_code == 200
    assert staff_me.status_code == 200
    assert admin_me.json()["email"] == ADMIN_EMAIL
    assert staff_me.json()["email"] == STAFF_EMAIL
    assert admin_me.json()["role"] == "admin"
    assert staff_me.json()["role"] == "staff"

    # Re-check admin_client after using staff_client, to confirm the
    # second login didn't clobber the first client's session.
    admin_me_again = admin_client.get("/auth/me")
    assert admin_me_again.status_code == 200
    assert admin_me_again.json()["email"] == ADMIN_EMAIL
