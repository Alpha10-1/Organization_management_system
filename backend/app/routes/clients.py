from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=list[ClientOut])
def list_clients(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Client)

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

    return query.order_by(Client.created_at.desc()).all()


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
    client = db.query(Client).filter(Client.id == client_id).first()

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
    client = db.query(Client).filter(Client.id == client_id).first()

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
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client_name = f"{client.first_name} {client.last_name}"

    db.delete(client)
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