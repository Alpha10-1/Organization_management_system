import pytest
from fastapi import HTTPException

from app.core import rate_limit


def test_allows_attempts_under_the_limit():
    for _ in range(rate_limit.EMAIL_MAX_ATTEMPTS - 1):
        rate_limit._check_and_record("email:test@org.com", rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)
    # Should not raise.


def test_blocks_once_limit_is_reached():
    key = "email:blocked@org.com"
    for _ in range(rate_limit.EMAIL_MAX_ATTEMPTS):
        rate_limit._check_and_record(key, rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)

    with pytest.raises(HTTPException) as exc_info:
        rate_limit._check_and_record(key, rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)

    assert exc_info.value.status_code == 429


def test_old_attempts_outside_window_are_forgotten(monkeypatch):
    key = "email:stale@org.com"
    fake_time = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: fake_time[0])

    for _ in range(rate_limit.EMAIL_MAX_ATTEMPTS):
        rate_limit._check_and_record(key, rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)

    # Jump forward past the window -- old attempts should no longer count.
    fake_time[0] += rate_limit.EMAIL_WINDOW_SECONDS + 1

    # Should not raise, since the earlier attempts have expired.
    rate_limit._check_and_record(key, rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)


def test_email_and_ip_limits_are_independent_keys():
    rate_limit._attempts.clear()
    for _ in range(rate_limit.EMAIL_MAX_ATTEMPTS):
        rate_limit._check_and_record("email:a@org.com", rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)

    # A different email under the same limit type should be unaffected.
    rate_limit._check_and_record("email:b@org.com", rate_limit.EMAIL_MAX_ATTEMPTS, rate_limit.EMAIL_WINDOW_SECONDS)
