import os
import secrets
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can still be set another way
    pass

# Values that must never be treated as a real secret, whether they come from
# the old hardcoded default or someone pasting a placeholder into .env
_INSECURE_SECRET_KEYS = {"", "change-this-in-production", "secret", "changeme"}


def _resolve_secret_key() -> str:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    secret_key = os.getenv("SECRET_KEY", "")

    if secret_key.strip().lower() not in _INSECURE_SECRET_KEYS:
        return secret_key

    if environment == "production":
        raise RuntimeError(
            "SECRET_KEY is not set (or is using an insecure placeholder). "
            "Refusing to start with ENVIRONMENT=production. Generate a real "
            "secret with:\n"
            '    python -c "import secrets; print(secrets.token_hex(32))"\n'
            "and set it via the SECRET_KEY environment variable."
        )

    # Dev/test fallback: keep the app runnable out of the box, but make the
    # tradeoff impossible to miss. Every restart invalidates existing tokens
    # (everyone gets logged out), which is intentional -- it's a nudge to set
    # a real SECRET_KEY rather than a bug.
    print(
        "WARNING: SECRET_KEY is not set. Using a temporary key generated for "
        "this run only -- all active sessions will be invalidated on every "
        "restart. Set the SECRET_KEY environment variable to fix this "
        "(see backend/.env.example).",
        file=sys.stderr,
    )
    return secrets.token_hex(32)


def _resolve_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if origins:
        return origins
    # Sensible default for local development only.
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


class Settings:
    APP_NAME = "Organization Management System API"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY = _resolve_secret_key()
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours
    CORS_ORIGINS = _resolve_cors_origins()
    # Cookies can only be marked Secure when served over HTTPS. Local dev
    # runs over plain http, so this defaults off unless explicitly in prod.
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes") or ENVIRONMENT == "production"


settings = Settings()
