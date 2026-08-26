from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import require_role
from app.core.permissions import PERMISSION_CATALOG, validate_permission_keys
from app.core.time import utcnow
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])

# Role/permission management is intentionally never delegable through
# the permission system it defines -- every route in this file is
# admin-only, full stop, regardless of any custom role a user holds.
# See app.models.role.Role's docstring for the reasoning.
AdminOnly = Depends(require_role("admin"))


@router.get("/catalog", response_model=dict[str, str])
def get_permission_catalog(current_user: UserPublic = AdminOnly):
    """The fixed set of permission keys a role's `permissions` list may
    contain, with a human-readable description of what each grants."""
    return PERMISSION_CATALOG


@router.get("/", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    current_user: UserPublic = AdminOnly,
):
    return db.query(Role).filter(Role.deleted_at.is_(None)).order_by(Role.name.asc()).all()


@router.post("/", response_model=RoleOut)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = AdminOnly,
):
    validate_permission_keys(payload.permissions)

    if db.query(Role).filter(Role.name == payload.name, Role.deleted_at.is_(None)).first():
        raise HTTPException(status_code=400, detail="A role with this name already exists")

    role = Role(
        name=payload.name,
        description=payload.description,
        permissions=payload.permissions,
        is_system=False,
        created_by_email=current_user.email,
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    log_activity(
        db=db,
        user=current_user,
        action="role_created",
        entity_type="role",
        entity_id=role.id,
        title=f"Role created: {role.name}",
        description=f"New custom role with permissions: {', '.join(role.permissions) or 'none'}.",
    )

    return role


@router.get("/{role_id}", response_model=RoleOut)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = AdminOnly,
):
    role = db.query(Role).filter(Role.id == role_id, Role.deleted_at.is_(None)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = AdminOnly,
):
    """Every role, including seeded system roles, has its permissions and
    description freely editable by an admin -- "customizable" applies to
    the built-in starting points too, not just wholly new roles. Only
    the name and existence of system roles are protected (see
    delete_role below)."""
    role = db.query(Role).filter(Role.id == role_id, Role.deleted_at.is_(None)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    updates = payload.model_dump(exclude_unset=True)

    if "permissions" in updates:
        validate_permission_keys(updates["permissions"])

    if "name" in updates and updates["name"] != role.name:
        if db.query(Role).filter(Role.name == updates["name"], Role.deleted_at.is_(None)).first():
            raise HTTPException(status_code=400, detail="A role with this name already exists")

    for key, value in updates.items():
        setattr(role, key, value)

    db.commit()
    db.refresh(role)

    log_activity(
        db=db,
        user=current_user,
        action="role_updated",
        entity_type="role",
        entity_id=role.id,
        title=f"Role updated: {role.name}",
        description=f"Permissions now: {', '.join(role.permissions) or 'none'}.",
    )

    return role


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = AdminOnly,
):
    role = db.query(Role).filter(Role.id == role_id, Role.deleted_at.is_(None)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(
            status_code=400,
            detail="System roles can't be deleted, only edited. Remove its permissions instead if you want it to grant nothing.",
        )

    assigned_count = db.query(User).filter(User.custom_role_id == role.id).count()
    if assigned_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"{assigned_count} user(s) still have this role assigned. Reassign them first.",
        )

    role.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="role_deleted",
        entity_type="role",
        entity_id=role.id,
        title=f"Role deleted: {role.name}",
        description="Custom role removed.",
    )

    return {"detail": "Role deleted"}
