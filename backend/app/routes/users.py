from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_user_by_email, require_role
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserPublic
from app.schemas.user_management import (
    UserCreate,
    UserDepartmentUpdate,
    UserManagementOut,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _guard_self_lockout(
    current_user: UserPublic,
    target: User,
    *,
    new_role: str | None = None,
    new_disabled: bool | None = None,
) -> None:
    """Block an admin from disabling their own account or demoting
    themselves away from admin. Both would (or could) lock them out of user
    management with no way back in short of direct DB access. Another admin
    always has to make these changes instead."""
    if current_user.email.lower() != target.email.lower():
        return

    if new_disabled is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account. Ask another admin to do this.",
        )

    if new_role is not None and new_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role away from admin. Ask another admin to do this.",
        )


@router.get("/", response_model=list[UserManagementOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    return db.query(User).order_by(User.id).all()


@router.post("/", response_model=UserManagementOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    email = payload.email.lower()

    if get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    if payload.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    user = User(
        name=payload.name,
        email=email,
        role=payload.role,
        disabled=False,
        hashed_password=get_password_hash(payload.password),
        department_id=payload.department_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity(
        db=db,
        user=current_user,
        action="user_created",
        entity_type="user",
        entity_id=user.id,
        title=f"User created: {user.name}",
        description=f"Created user '{user.email}' with role '{user.role}'.",
    )

    return user


@router.put("/{email}", response_model=UserManagementOut)
def update_user(
    email: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = get_user_by_email(db, email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    _guard_self_lockout(current_user, target, new_role=payload.role, new_disabled=payload.disabled)

    if payload.name is not None:
        target.name = payload.name

    if payload.role is not None:
        if payload.role not in ["admin", "staff"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        target.role = payload.role

    if payload.disabled is not None:
        target.disabled = payload.disabled

    if payload.department_id is not None:
        target.department_id = payload.department_id

    db.commit()
    db.refresh(target)

    log_activity(
        db=db,
        user=current_user,
        action="user_updated",
        entity_type="user",
        entity_id=target.id,
        title=f"User updated: {target.name}",
        description=f"Updated user '{target.email}'.",
    )

    return target


@router.patch("/{email}/role", response_model=UserManagementOut)
def update_user_role(
    email: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = get_user_by_email(db, email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role not in ["admin", "staff"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    _guard_self_lockout(current_user, target, new_role=payload.role)

    target.role = payload.role

    db.commit()
    db.refresh(target)

    log_activity(
        db=db,
        user=current_user,
        action="user_role_updated",
        entity_type="user",
        entity_id=target.id,
        title=f"User role changed: {target.name}",
        description=f"Changed role to '{target.role}' for '{target.email}'.",
    )

    return target


@router.patch("/{email}/status", response_model=UserManagementOut)
def update_user_status(
    email: str,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = get_user_by_email(db, email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    _guard_self_lockout(current_user, target, new_disabled=payload.disabled)

    target.disabled = payload.disabled

    db.commit()
    db.refresh(target)

    log_activity(
        db=db,
        user=current_user,
        action="user_status_updated",
        entity_type="user",
        entity_id=target.id,
        title=f"User status changed: {target.name}",
        description=f"Set disabled={target.disabled} for '{target.email}'.",
    )

    return target


@router.patch("/{email}/department", response_model=UserManagementOut)
def update_user_department(
    email: str,
    payload: UserDepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = get_user_by_email(db, email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.department_id = payload.department_id

    db.commit()
    db.refresh(target)

    log_activity(
        db=db,
        user=current_user,
        action="user_department_updated",
        entity_type="user",
        entity_id=target.id,
        title=f"Department changed: {target.name}",
        description=f"Updated department for '{target.email}'.",
    )

    return target
