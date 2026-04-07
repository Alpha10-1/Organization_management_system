from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.core.fake_db import fake_users_db
from app.core.security import decode_access_token
from app.schemas.user import UserPublic

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_by_email(email: str):
    return fake_users_db.get(email)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = get_user_by_email(email)
    if not user:
        raise credentials_exception

    return UserPublic(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        disabled=user["disabled"],
    )


async def get_current_active_user(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(*allowed_roles: str):
    async def role_checker(
        current_user: UserPublic = Depends(get_current_active_user),
    ) -> UserPublic:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker