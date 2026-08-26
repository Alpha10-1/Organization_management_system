from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.department_scope import require_scoped_write
from app.core.permissions import user_has_permission
from app.core.time import utcnow
from app.db.session import get_db
from app.core.client_health import compute_client_health
from app.models.client import Client
from app.models.client_contact import ClientContact
from app.models.client_note import ClientNote
from app.schemas.client import (
    ClientBulkStatusUpdate,
    ClientCreate,
    ClientHealth,
    ClientOut,
    ClientUpdate,
)
from app.schemas.client_contact import ClientContactCreate, ClientContactOut, ClientContactUpdate
from app.schemas.client_note import ClientNoteCreate, ClientNoteOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/clients", tags=["Clients"])

VALID_STATUSES = {"Active", "Pending", "Closed"}
VALID_CLIENT_TYPES = {"business", "individual", "npo"}

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200


def _validate_client_payload(client_type: str, first_name, last_name, company_name) -> None:
    if client_type not in VALID_CLIENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid client_type. Must be one of: {sorted(VALID_CLIENT_TYPES)}")
    if client_type == "individual":
        if not first_name or not last_name:
            raise HTTPException(status_code=400, detail="Individual clients require first_name and last_name")
    else:
        if not company_name:
            raise HTTPException(status_code=400, detail=f"{client_type.capitalize()} clients require company_name")


@router.get("/", response_model=list[ClientOut])
def list_clients(
    response: Response,
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    tag_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Client).filter(Client.deleted_at.is_(None))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Client.first_name.ilike(search_term),
                Client.last_name.ilike(search_term),
                Client.company_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.email.ilike(search_term),
            )
        )

    if status:
        query = query.filter(Client.status == status)

    if department_id is not None:
        query = query.filter(Client.department_id == department_id)

    if tag_id is not None:
        from app.models.tag import ClientTag

        query = query.join(ClientTag, ClientTag.client_id == Client.id).filter(ClientTag.tag_id == tag_id)

    response.headers["X-Total-Count"] = str(query.count())

    return (
        query.order_by(Client.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=ClientOut)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if client.parent_client_id is not None:
        parent = (
            db.query(Client)
            .filter(Client.id == client.parent_client_id, Client.deleted_at.is_(None))
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent client not found")

    _validate_client_payload(client.client_type, client.first_name, client.last_name, client.company_name)

    require_scoped_write(db, current_user, client.department_id)

    new_client = Client(**client.model_dump())
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    log_activity(
        db=db,
        user=current_user,
        action="client_created",
        entity_type="client",
        entity_id=new_client.id,
        title=f"Client created: {new_client.display_name}",
        description=f"Created {new_client.client_type} client record with status '{new_client.status}'.",
    )

    return new_client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.deleted_at.is_(None))
        .first()
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.deleted_at.is_(None))
        .first()
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = payload.model_dump(exclude_unset=True)

    require_scoped_write(db, current_user, client.department_id)
    if "department_id" in updates and updates["department_id"] != client.department_id:
        # Reassigning a client into a different department requires
        # write access to that department too, not just the current one --
        # otherwise a staff member could move a client out of a department
        # they don't manage into one they do (or vice versa) to dodge scope.
        require_scoped_write(db, current_user, updates["department_id"])

    if "parent_client_id" in updates and updates["parent_client_id"] is not None:
        if updates["parent_client_id"] == client_id:
            raise HTTPException(status_code=400, detail="A client cannot be its own parent")
        parent = (
            db.query(Client)
            .filter(Client.id == updates["parent_client_id"], Client.deleted_at.is_(None))
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent client not found")

    if "relationship_health" in updates and updates["relationship_health"] is not None:
        from app.core.client_health import VALID_HEALTH_VALUES

        if updates["relationship_health"] not in VALID_HEALTH_VALUES:
            raise HTTPException(status_code=400, detail=f"Invalid relationship_health. Must be one of: {sorted(VALID_HEALTH_VALUES)}")

    merged_type = updates.get("client_type", client.client_type)
    merged_first = updates.get("first_name", client.first_name)
    merged_last = updates.get("last_name", client.last_name)
    merged_company = updates.get("company_name", client.company_name)
    _validate_client_payload(merged_type, merged_first, merged_last, merged_company)

    for key, value in updates.items():
        setattr(client, key, value)

    db.commit()
    db.refresh(client)

    log_activity(
        db=db,
        user=current_user,
        action="client_updated",
        entity_type="client",
        entity_id=client.id,
        title=f"Client updated: {client.display_name}",
        description="Client record updated.",
    )

    return client


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.deleted_at.is_(None))
        .first()
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    require_scoped_write(db, current_user, client.department_id)

    client_name = client.display_name

    # Soft delete: keep the row (and any files/activity referencing it)
    # for audit/recovery, just hide it from normal queries.
    client.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="client_deleted",
        entity_type="client",
        entity_id=client_id,
        title=f"Client deleted: {client_name}",
        description="Client record removed from the system.",
    )

    return {"message": "Client deleted successfully"}


@router.post("/bulk/status")
def bulk_update_status(
    payload: ClientBulkStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    if not payload.client_ids:
        raise HTTPException(status_code=400, detail="No client IDs provided")

    clients = (
        db.query(Client)
        .filter(Client.id.in_(payload.client_ids), Client.deleted_at.is_(None))
        .all()
    )

    allowed_clients = []
    for client in clients:
        try:
            require_scoped_write(db, current_user, client.department_id)
            allowed_clients.append(client)
        except HTTPException:
            continue

    if not allowed_clients:
        raise HTTPException(status_code=403, detail="You don't have write access to any of these clients")

    for client in allowed_clients:
        client.status = payload.status

    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="client_bulk_status_updated",
        entity_type="client",
        title=f"Bulk status update: {len(allowed_clients)} client(s) -> {payload.status}",
        description=f"Set status to '{payload.status}' for {len(allowed_clients)} client(s).",
    )

    return {"message": f"Updated {len(allowed_clients)} client(s)", "updated": len(allowed_clients)}


@router.get("/{client_id}/notes", response_model=list[ClientNoteOut])
def list_client_notes(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return (
        db.query(ClientNote)
        .filter(ClientNote.client_id == client_id, ClientNote.deleted_at.is_(None))
        .order_by(ClientNote.created_at.desc())
        .all()
    )


@router.post("/{client_id}/notes", response_model=ClientNoteOut)
def add_client_note(
    client_id: int,
    payload: ClientNoteCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.deleted_at.is_(None))
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    require_scoped_write(db, current_user, client.department_id)

    note = ClientNote(
        client_id=client_id,
        author_email=current_user.email,
        author_name=current_user.name,
        body=payload.body,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    log_activity(
        db=db,
        user=current_user,
        action="client_note_added",
        entity_type="client",
        entity_id=client_id,
        title=f"Note added: {client.display_name}",
        description=payload.body[:200],
    )

    return note


@router.delete("/{client_id}/notes/{note_id}")
def delete_client_note(
    client_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    note = (
        db.query(ClientNote)
        .filter(ClientNote.id == note_id, ClientNote.client_id == client_id, ClientNote.deleted_at.is_(None))
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.author_email != current_user.email and not user_has_permission(db, current_user, "content.moderate"):
        raise HTTPException(status_code=403, detail="You can only delete your own notes")

    note.deleted_at = utcnow()
    db.commit()
    return {"message": "Note deleted"}


# --- Relationship health -----------------------------------------------


@router.get("/{client_id}/health", response_model=ClientHealth)
def get_client_health(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    computed = compute_client_health(db, client_id)
    is_override = client.relationship_health is not None

    return ClientHealth(
        client_id=client_id,
        health=client.relationship_health if is_override else computed["computed_health"],
        computed_health=computed["computed_health"],
        is_manual_override=is_override,
        overdue_task_count=computed["overdue_task_count"],
        open_engagement_count=computed["open_engagement_count"],
        contracts_expiring_soon=computed["contracts_expiring_soon"],
        reasons=computed["reasons"],
    )


# --- Contacts ------------------------------------------------------------


@router.get("/{client_id}/contacts", response_model=list[ClientContactOut])
def list_client_contacts(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return (
        db.query(ClientContact)
        .filter(ClientContact.client_id == client_id, ClientContact.deleted_at.is_(None))
        .order_by(ClientContact.is_primary.desc(), ClientContact.created_at.asc())
        .all()
    )


@router.post("/{client_id}/contacts", response_model=ClientContactOut)
def add_client_contact(
    client_id: int,
    payload: ClientContactCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    require_scoped_write(db, current_user, client.department_id)

    if payload.is_primary:
        # Only one primary contact per client: demote any existing one.
        db.query(ClientContact).filter(
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
            ClientContact.is_primary.is_(True),
        ).update({"is_primary": False})

    contact = ClientContact(client_id=client_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)

    log_activity(
        db=db,
        user=current_user,
        action="client_contact_added",
        entity_type="client",
        entity_id=client_id,
        title=f"Contact added: {contact.name}",
        description=f"Added contact '{contact.name}' ({contact.role or 'no role'}) to {client.display_name}.",
    )

    return contact


@router.put("/{client_id}/contacts/{contact_id}", response_model=ClientContactOut)
def update_client_contact(
    client_id: int,
    contact_id: int,
    payload: ClientContactUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    contact = (
        db.query(ClientContact)
        .filter(
            ClientContact.id == contact_id,
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    client = db.query(Client).filter(Client.id == client_id).first()
    require_scoped_write(db, current_user, client.department_id if client else None)

    updates = payload.model_dump(exclude_unset=True)

    if updates.get("is_primary"):
        db.query(ClientContact).filter(
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
            ClientContact.id != contact_id,
            ClientContact.is_primary.is_(True),
        ).update({"is_primary": False})

    for key, value in updates.items():
        setattr(contact, key, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{client_id}/contacts/{contact_id}")
def delete_client_contact(
    client_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    contact = (
        db.query(ClientContact)
        .filter(
            ClientContact.id == contact_id,
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    client = db.query(Client).filter(Client.id == client_id).first()
    require_scoped_write(db, current_user, client.department_id if client else None)

    contact.deleted_at = utcnow()
    db.commit()
    return {"message": "Contact deleted successfully"}