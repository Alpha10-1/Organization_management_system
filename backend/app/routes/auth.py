import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.config import settings
from app.core.deps import AUTH_COOKIE_NAME, get_current_active_user, get_user_by_email
from app.core.email import send_password_reset_email, send_verification_email
from app.core.rate_limit import check_login_rate_limit, reset_login_rate_limit
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.time import utcnow
from app.db.session import get_db
from app.schemas.auth import (
    EmailVerificationConfirm,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
)
from app.schemas.user import UserPublic

RESET_TOKEN_EXPIRE = timedelta(hours=1)
VERIFICATION_TOKEN_EXPIRE = timedelta(hours=24)

router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_MAX_AGE_SECONDS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email.lower())
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    check_login_rate_limit(request, form_data.username)

    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled",
        )

    reset_login_rate_limit(request, form_data.username)

    user_public = UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        disabled=user.disabled,
        is_verified=user.is_verified,
    )

    log_activity(
        db=db,
        user=user_public,
        action="login",
        entity_type="auth",
        title="User signed in",
        description=f"{user_public.name} signed into the system.",
    )

    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "name": user.name,
        }
    )

    # Primary auth mechanism: httpOnly cookie, so the token is never
    # readable from JS (mitigates token theft via XSS). The token is also
    # returned in the response body for API clients (Swagger, scripts)
    # that can't rely on browser cookie handling.
    _set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_active_user)):
    return current_user


@router.post("/request-password-reset")
async def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email.lower())

    # Always return the same response whether or not the account exists,
    # so this endpoint can't be used to enumerate registered emails.
    generic_response = {
        "message": "If an account with that email exists, a password reset link has been sent."
    }

    if not user or user.disabled:
        return generic_response

    user.reset_token = secrets.token_urlsafe(32)
    user.reset_token_expires = utcnow() + RESET_TOKEN_EXPIRE
    db.commit()

    send_password_reset_email(db, user.email, user.name, user.reset_token)

    return generic_response


@router.post("/reset-password")
async def reset_password(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    from app.models.user import User  # local import avoids a circular import at module load

    user = db.query(User).filter(User.reset_token == payload.token).first()

    if not user or not user.reset_token_expires or user.reset_token_expires < utcnow():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}


@router.post("/request-verification")
async def request_verification(
    current_user: UserPublic = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from app.models.user import User

    user = get_user_by_email(db, current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"message": "This account is already verified."}

    user.verification_token = secrets.token_urlsafe(32)
    user.verification_token_expires = utcnow() + VERIFICATION_TOKEN_EXPIRE
    db.commit()

    send_verification_email(db, user.email, user.name, user.verification_token)

    return {"message": "Verification email sent."}


@router.post("/verify-email")
async def verify_email(
    payload: EmailVerificationConfirm,
    db: Session = Depends(get_db),
):
    from app.models.user import User

    user = db.query(User).filter(User.verification_token == payload.token).first()

    if (
        not user
        or not user.verification_token_expires
        or user.verification_token_expires < utcnow()
    ):
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    return {"message": "Email verified successfully."}