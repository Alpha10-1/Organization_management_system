from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.config import settings
from app.core.deps import AUTH_COOKIE_NAME, get_current_active_user, get_user_by_email
from app.core.rate_limit import check_login_rate_limit, reset_login_rate_limit
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.schemas.auth import Token
from app.schemas.user import UserPublic

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