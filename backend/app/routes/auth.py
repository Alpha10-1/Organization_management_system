from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.fake_db import fake_users_db
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.schemas.auth import Token
from app.schemas.user import UserPublic

router = APIRouter(prefix="/auth", tags=["Authentication"])


def authenticate_user(email: str, password: str):
    user = fake_users_db.get(email)
    if not user:
        return None

    if not verify_password(password, user["hashed_password"]):
        return None

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_public = UserPublic(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        disabled=user["disabled"],
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
            "sub": user["email"],
            "role": user["role"],
            "name": user["name"],
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_active_user)):
    return current_user