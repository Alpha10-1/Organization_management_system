"""Lightweight in-memory rate limiting for login attempts.

Two independent windows are enforced:
  - per account (email): stops one attacker from brute-forcing a single
    user's password, regardless of how many source IPs they use
  - per source IP: stops one attacker from credential-stuffing many
    different accounts from the same origin

This is intentionally dependency-free and process-local. It's a good fit
for the single-process dev/small-deployment setup this app currently runs
as. If the app is ever run with multiple worker processes or replicas
behind a load balancer, replace this with a shared store (e.g. Redis) so
all workers see the same attempt counts.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

EMAIL_WINDOW_SECONDS = 5 * 60
EMAIL_MAX_ATTEMPTS = 5

IP_WINDOW_SECONDS = 5 * 60
IP_MAX_ATTEMPTS = 20

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_and_record(key: str, max_attempts: int, window_seconds: int) -> None:
    now = time.monotonic()

    with _lock:
        attempts = _attempts[key]
        attempts[:] = [t for t in attempts if now - t < window_seconds]

        if len(attempts) >= max_attempts:
            retry_after = int(window_seconds - (now - attempts[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        attempts.append(now)


def check_login_rate_limit(request: Request, email: str) -> None:
    """Call before validating credentials on every login attempt. Raises
    HTTPException(429) if either the account or the source IP has exceeded
    its allowed attempts in the current window."""
    ip = _client_ip(request)
    normalized_email = email.strip().lower()

    _check_and_record(f"ip:{ip}", IP_MAX_ATTEMPTS, IP_WINDOW_SECONDS)
    _check_and_record(f"email:{normalized_email}", EMAIL_MAX_ATTEMPTS, EMAIL_WINDOW_SECONDS)


def reset_login_rate_limit(request: Request, email: str) -> None:
    """Call after a successful login so legitimate users aren't penalized
    by earlier failed attempts (their own typos, etc.)."""
    ip = _client_ip(request)
    normalized_email = email.strip().lower()

    with _lock:
        _attempts.pop(f"ip:{ip}", None)
        _attempts.pop(f"email:{normalized_email}", None)
