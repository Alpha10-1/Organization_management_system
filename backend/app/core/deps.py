from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserPublic

AUTH_COOKIE_NAME = "access_token"

# auto_error=False: don't 401 just because the Authorization header is
# missing -- a valid session might still be present via the httpOnly
# cookie set at login. get_current_user checks both below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def _extract_token(request: Request, header_token: str | None) -> str | None:
    if header_token:
        return header_token
    return request.cookies.get(AUTH_COOKIE_NAME)


async def get_current_user(
    request: Request,
    header_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = _extract_token(request, header_token)
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if not user:
        raise credentials_exception

    return UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        disabled=user.disabled,
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