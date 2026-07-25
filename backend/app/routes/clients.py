from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.time import utcnow
from app.db.session import get_db
from app.models.client import Client
from app.models.client_note import ClientNote
from app.schemas.client import (
    ClientBulkStatusUpdate,
    ClientCreate,
    ClientOut,
    ClientUpdate,
)
from app.schemas.client_note import ClientNoteCreate, ClientNoteOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/clients", tags=["Clients"])

VALID_STATUSES = {"Active", "Pending", "Closed"}

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200


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
        title=f"Client created: {new_client.first_name} {new_client.last_name}",
        description=f"Created client record with status '{new_client.status}'.",
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
        title=f"Client updated: {client.first_name} {client.last_name}",
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

    client_name = f"{client.first_name} {client.last_name}"

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

    for client in clients:
        client.status = payload.status

    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="client_bulk_status_updated",
        entity_type="client",
        title=f"Bulk status update: {len(clients)} client(s) -> {payload.status}",
        description=f"Set status to '{payload.status}' for {len(clients)} client(s).",
    )

    return {"message": f"Updated {len(clients)} client(s)", "updated": len(clients)}


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
        title=f"Note added: {client.first_name} {client.last_name}",
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

    if note.author_email != current_user.email and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only delete your own notes")

    note.deleted_at = utcnow()
    db.commit()
    return {"message": "Note deleted"}