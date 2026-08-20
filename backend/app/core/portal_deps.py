from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.client_portal_user import ClientPortalUser
from app.schemas.client_portal_user import PortalUserPublic

# Separate cookie from the staff AUTH_COOKIE_NAME (app.core.deps) so a
# person can be logged into the staff app and the client portal at the
# same time in the same browser without one login clobbering the other,
# and so a portal session is never accidentally readable by staff routes
# that only look at the staff cookie.
PORTAL_AUTH_COOKIE_NAME = "portal_access_token"

# actor="client" is baked into every portal token at issuance (see
# routes/portal_auth.py) and checked on both sides below -- a token
# missing or mismatching this claim is rejected here even if it would
# otherwise decode fine, so a staff token can never be replayed against
# portal routes (or vice versa; see the matching check added to
# app.core.deps.get_current_user) even if the same person happens to share
# an email between a staff account and a portal account.
PORTAL_TOKEN_ACTOR = "client"

oauth2_scheme_portal = OAuth2PasswordBearer(tokenUrl="/portal/auth/login", auto_error=False)


def get_portal_user_by_email(db: Session, email: str) -> ClientPortalUser | None:
    return (
        db.query(ClientPortalUser)
        .filter(ClientPortalUser.email == email, ClientPortalUser.deleted_at.is_(None))
        .first()
    )


def _extract_portal_token(request: Request, header_token: str | None) -> str | None:
    if header_token:
        return header_token
    return request.cookies.get(PORTAL_AUTH_COOKIE_NAME)


async def get_current_portal_user(
    request: Request,
    header_token: str | None = Depends(oauth2_scheme_portal),
    db: Session = Depends(get_db),
) -> PortalUserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = _extract_portal_token(request, header_token)
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email is None or payload.get("actor") != PORTAL_TOKEN_ACTOR:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    portal_user = get_portal_user_by_email(db, email)
    if not portal_user:
        raise credentials_exception

    return PortalUserPublic(
        id=portal_user.id,
        client_id=portal_user.client_id,
        name=portal_user.name,
        email=portal_user.email,
        disabled=portal_user.disabled,
    )


async def get_current_active_portal_user(
    current_portal_user: PortalUserPublic = Depends(get_current_portal_user),
) -> PortalUserPublic:
    if current_portal_user.disabled:
        raise HTTPException(status_code=400, detail="This portal account has been disabled")
    return current_portal_user
