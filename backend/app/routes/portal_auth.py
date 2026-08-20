import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_portal_password_reset_email
from app.core.portal_deps import (
    PORTAL_AUTH_COOKIE_NAME,
    PORTAL_TOKEN_ACTOR,
    get_current_active_portal_user,
    get_portal_user_by_email,
)
from app.core.rate_limit import check_login_rate_limit, reset_login_rate_limit
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.time import utcnow
from app.db.session import get_db
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest, Token
from app.schemas.client_portal_user import PortalUserPublic

RESET_TOKEN_EXPIRE = timedelta(hours=1)

router = APIRouter(prefix="/portal/auth", tags=["Client Portal Auth"])

COOKIE_MAX_AGE_SECONDS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_portal_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=PORTAL_AUTH_COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _authenticate_portal_user(db: Session, email: str, password: str):
    portal_user = get_portal_user_by_email(db, email.lower())
    if not portal_user:
        return None
    if not verify_password(password, portal_user.hashed_password):
        return None
    return portal_user


@router.post("/login", response_model=Token)
async def portal_login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Shares the same rate limiter (keyed by email+ip) as staff login --
    # brute-force protection shouldn't be weaker just because this is the
    # client-facing door.
    check_login_rate_limit(request, form_data.username)

    portal_user = _authenticate_portal_user(db, form_data.username, form_data.password)

    if not portal_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if portal_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This portal account has been disabled",
        )

    reset_login_rate_limit(request, form_data.username)

    portal_user.last_login_at = utcnow()
    db.commit()

    access_token = create_access_token(
        data={
            "sub": portal_user.email,
            "actor": PORTAL_TOKEN_ACTOR,
            "client_id": portal_user.client_id,
            "name": portal_user.name,
        }
    )

    _set_portal_auth_cookie(response, access_token)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def portal_logout(response: Response):
    response.delete_cookie(key=PORTAL_AUTH_COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=PortalUserPublic)
async def portal_me(current_portal_user: PortalUserPublic = Depends(get_current_active_portal_user)):
    return current_portal_user


@router.post("/request-password-reset")
async def portal_request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    from app.models.client_portal_user import ClientPortalUser  # local import avoids circular import at load

    portal_user = get_portal_user_by_email(db, payload.email.lower())

    # Same enumeration-resistant response regardless of whether the
    # account exists, matching the staff reset flow.
    generic_response = {
        "message": "If a portal account with that email exists, a password reset link has been sent."
    }

    if not portal_user or portal_user.disabled:
        return generic_response

    portal_user.reset_token = secrets.token_urlsafe(32)
    portal_user.reset_token_expires = utcnow() + RESET_TOKEN_EXPIRE
    db.commit()

    send_portal_password_reset_email(db, portal_user.email, portal_user.name, portal_user.reset_token)

    return generic_response


@router.post("/reset-password")
async def portal_reset_password(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    from app.models.client_portal_user import ClientPortalUser

    portal_user = (
        db.query(ClientPortalUser)
        .filter(ClientPortalUser.reset_token == payload.token, ClientPortalUser.deleted_at.is_(None))
        .first()
    )

    if not portal_user or not portal_user.reset_token_expires:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    # reset_token_expires round-trips through SQLite as a naive datetime
    # (the Column isn't timezone-aware), but utcnow() returns tz-aware --
    # comparing them directly raises TypeError once the ORM object has
    # been expired and reloaded (e.g. after a prior commit in this
    # request). Normalize both sides to naive UTC before comparing.
    expires = portal_user.reset_token_expires
    now_naive = utcnow().replace(tzinfo=None)
    if expires.tzinfo is not None:
        expires = expires.replace(tzinfo=None)
    if expires < now_naive:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    portal_user.hashed_password = get_password_hash(payload.new_password)
    portal_user.reset_token = None
    portal_user.reset_token_expires = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}
