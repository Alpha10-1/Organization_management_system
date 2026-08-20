import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.department_scope import require_scoped_write
from app.core.email import send_portal_invite_email
from app.core.security import get_password_hash
from app.core.time import utcnow
from app.db.session import get_db
from app.models.client import Client
from app.models.client_contact import ClientContact
from app.models.client_portal_user import ClientPortalUser
from app.schemas.client_portal_user import ClientPortalUserInvite, ClientPortalUserOut, ClientPortalUserUpdate
from app.schemas.user import UserPublic

# Nested under /clients to match the existing /clients/{client_id}/contacts
# and /clients/{client_id}/notes convention -- a portal user is scoped to
# exactly one client, same as those.
router = APIRouter(prefix="/clients", tags=["Client Portal Users"])

INVITE_TOKEN_EXPIRE = timedelta(hours=24)


@router.get("/{client_id}/portal-users", response_model=list[ClientPortalUserOut])
def list_portal_users(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return (
        db.query(ClientPortalUser)
        .filter(ClientPortalUser.client_id == client_id, ClientPortalUser.deleted_at.is_(None))
        .order_by(ClientPortalUser.created_at.asc())
        .all()
    )


@router.post("/{client_id}/portal-users", response_model=ClientPortalUserOut)
def invite_portal_user(
    client_id: int,
    payload: ClientPortalUserInvite,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    require_scoped_write(db, current_user, client.department_id)

    email = payload.email.lower()
    existing = db.query(ClientPortalUser).filter(ClientPortalUser.email == email).first()
    if existing and existing.deleted_at is None:
        raise HTTPException(status_code=400, detail="A portal account with this email already exists")

    if payload.client_contact_id is not None:
        contact = (
            db.query(ClientContact)
            .filter(
                ClientContact.id == payload.client_contact_id,
                ClientContact.client_id == client_id,
                ClientContact.deleted_at.is_(None),
            )
            .first()
        )
        if not contact:
            raise HTTPException(status_code=404, detail="Client contact not found")

    # No usable password is set at invite time -- get_password_hash on a
    # random, never-communicated string means the account simply can't be
    # logged into until the client follows the invite link and sets one
    # via the same reset-token flow used for forgot-password.
    portal_user = ClientPortalUser(
        client_id=client_id,
        client_contact_id=payload.client_contact_id,
        name=payload.name,
        email=email,
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        invited_by_email=current_user.email,
        invited_by_name=current_user.name,
        reset_token=secrets.token_urlsafe(32),
        reset_token_expires=utcnow() + INVITE_TOKEN_EXPIRE,
    )
    db.add(portal_user)
    db.commit()
    db.refresh(portal_user)

    send_portal_invite_email(db, portal_user.email, portal_user.name, client.display_name, portal_user.reset_token)

    log_activity(
        db=db,
        user=current_user,
        action="portal_user_invited",
        entity_type="client",
        entity_id=client_id,
        title=f"Portal access invited: {portal_user.name}",
        description=f"Invited {portal_user.name} ({portal_user.email}) to the client portal for {client.display_name}.",
    )

    return portal_user


@router.put("/{client_id}/portal-users/{portal_user_id}", response_model=ClientPortalUserOut)
def update_portal_user(
    client_id: int,
    portal_user_id: int,
    payload: ClientPortalUserUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    portal_user = (
        db.query(ClientPortalUser)
        .filter(
            ClientPortalUser.id == portal_user_id,
            ClientPortalUser.client_id == client_id,
            ClientPortalUser.deleted_at.is_(None),
        )
        .first()
    )
    if not portal_user:
        raise HTTPException(status_code=404, detail="Portal user not found")

    client = db.query(Client).filter(Client.id == client_id).first()
    require_scoped_write(db, current_user, client.department_id if client else None)

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(portal_user, key, value)

    db.commit()
    db.refresh(portal_user)

    log_activity(
        db=db,
        user=current_user,
        action="portal_user_updated",
        entity_type="client",
        entity_id=client_id,
        title=f"Portal access updated: {portal_user.name}",
        description=(
            f"Disabled portal access for {portal_user.name}."
            if updates.get("disabled")
            else f"Updated portal account for {portal_user.name}."
        ),
    )

    return portal_user


@router.delete("/{client_id}/portal-users/{portal_user_id}")
def revoke_portal_user(
    client_id: int,
    portal_user_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    portal_user = (
        db.query(ClientPortalUser)
        .filter(
            ClientPortalUser.id == portal_user_id,
            ClientPortalUser.client_id == client_id,
            ClientPortalUser.deleted_at.is_(None),
        )
        .first()
    )
    if not portal_user:
        raise HTTPException(status_code=404, detail="Portal user not found")

    client = db.query(Client).filter(Client.id == client_id).first()
    require_scoped_write(db, current_user, client.department_id if client else None)

    portal_user.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="portal_user_revoked",
        entity_type="client",
        entity_id=client_id,
        title=f"Portal access revoked: {portal_user.name}",
        description=f"Revoked client portal access for {portal_user.name} ({portal_user.email}).",
    )

    return {"message": "Portal access revoked"}
