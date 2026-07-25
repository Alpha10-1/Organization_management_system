import os
import tempfile

import pytest

# DATABASE_URL/SECRET_KEY are resolved once at import time (app/core/config.py,
# app/db/session.py), so they must be set before any `app.*` module is
# imported anywhere in the test session -- including by other test files
# collected first. This isolates tests from the real dev database.
_tmp_dir = tempfile.mkdtemp(prefix="oms-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_dir}/test.db")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-do-not-use-in-prod")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_tmp_dir, "uploads"))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.rate_limit import _attempts  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_EMAIL = "admin@org.com"
ADMIN_PASSWORD = "Admin123!"
STAFF_EMAIL = "staff@org.com"
STAFF_PASSWORD = "Staff123!"


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    """Login rate limiting is process-global (see rate_limit.py), which
    would otherwise let earlier tests' failed attempts bleed into later
    ones and make the suite order-dependent."""
    _attempts.clear()
    yield
    _attempts.clear()


@pytest.fixture
def client():
    """A fresh, unauthenticated client. TestClient persists cookies across
    requests made with the same instance, same as a browser tab would."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_client(client):
    resp = client.post(
        "/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest.fixture
def staff_client(client):
    resp = client.post(
        "/auth/login",
        data={"username": STAFF_EMAIL, "password": STAFF_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return client
