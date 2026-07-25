from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, require_role
from app.db.session import get_db
from app.models.client import Client
from app.models.tag import ClientTag, Tag
from app.schemas.tag import TagCreate, TagOut, TagUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("/", response_model=list[TagOut])
def list_tags(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return db.query(Tag).order_by(Tag.name).all()


@router.post("/", response_model=TagOut)
def create_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if db.query(Tag).filter(Tag.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A tag with this name already exists")

    tag = Tag(name=payload.name, color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=TagOut)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(tag, key, value)

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.query(ClientTag).filter(ClientTag.tag_id == tag_id).delete()
    db.delete(tag)
    db.commit()
    return {"message": "Tag deleted successfully"}


@router.get("/clients/{client_id}", response_model=list[TagOut])
def get_client_tags(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return (
        db.query(Tag)
        .join(ClientTag, ClientTag.tag_id == Tag.id)
        .filter(ClientTag.client_id == client_id)
        .all()
    )


@router.post("/clients/{client_id}/{tag_id}")
def assign_tag_to_client(
    client_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = (
        db.query(ClientTag)
        .filter(ClientTag.client_id == client_id, ClientTag.tag_id == tag_id)
        .first()
    )
    if existing:
        return {"message": "Tag already assigned"}

    db.add(ClientTag(client_id=client_id, tag_id=tag_id))
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="client_tag_added",
        entity_type="client",
        entity_id=client_id,
        title=f"Tag added: {tag.name}",
        description=f"Tagged {client.first_name} {client.last_name} with '{tag.name}'.",
    )

    return {"message": "Tag assigned"}


@router.delete("/clients/{client_id}/{tag_id}")
def remove_tag_from_client(
    client_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    link = (
        db.query(ClientTag)
        .filter(ClientTag.client_id == client_id, ClientTag.tag_id == tag_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Tag is not assigned to this client")

    db.delete(link)
    db.commit()
    return {"message": "Tag removed"}
