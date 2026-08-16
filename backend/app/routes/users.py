from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_user_by_email, require_role
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import POSITION_LEVELS, User
from app.schemas.user import UserPublic
from app.schemas.user_management import (
    UserCreate,
    UserDepartmentUpdate,
    UserManagementOut,
    UserPositionUpdate,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _validate_position(position: str | None) -> None:
    if position is not None and position not in POSITION_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid position. Must be one of: {', '.join(POSITION_LEVELS)}",
        )


def _has_manager_cycle(db: Session, user_id: int, manager_id: int) -> bool:
    """True if setting user_id's manager to manager_id would create a
    reporting-line cycle, i.e. manager_id (transitively) already reports
    to user_id. Same walk-the-chain approach as task dependency cycle
    detection."""
    seen = set()
    current_id = manager_id
    while current_id is not None:
        if current_id == user_id:
            return True
        if current_id in seen:
            break
        seen.add(current_id)
        current_id = (
            db.query(User.manager_id).filter(User.id == current_id).scalar()
        )
    return False


def _apply_manager(db: Session, target: User, manager_id: int | None) -> None:
    if manager_id is None:
        target.manager_id = None
        return
    if manager_id == target.id:
        raise HTTPException(status_code=400, detail="A user cannot manage themselves")
    manager = db.query(User).filter(User.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=400, detail="Manager not found")
    if _has_manager_cycle(db, target.id, manager_id):
        raise HTTPException(
            status_code=400, detail="This assignment would create a reporting-line cycle"
        )
    target.manager_id = manager_id


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

    _validate_position(payload.position)

    user = User(
        name=payload.name,
        email=email,
        role=payload.role,
        disabled=False,
        hashed_password=get_password_hash(payload.password),
        department_id=payload.department_id,
        position=payload.position,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    if payload.manager_id is not None:
        _apply_manager(db, user, payload.manager_id)
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

    if payload.position is not None:
        _validate_position(payload.position)
        target.position = payload.position

    if payload.manager_id is not None:
        _apply_manager(db, target, payload.manager_id)

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


@router.patch("/{email}/position", response_model=UserManagementOut)
def update_user_position(
    email: str,
    payload: UserPositionUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = get_user_by_email(db, email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    _validate_position(payload.position)
    target.position = payload.position

    if "manager_id" in payload.model_fields_set:
        _apply_manager(db, target, payload.manager_id)

    db.commit()
    db.refresh(target)

    log_activity(
        db=db,
        user=current_user,
        action="user_position_updated",
        entity_type="user",
        entity_id=target.id,
        title=f"Position changed: {target.name}",
        description=f"Set position to '{target.position or 'none'}' for '{target.email}'.",
    )

    return target


@router.get("/org-chart")
def get_org_chart(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    """Firm-wide reporting-line tree: every user with no manager at the
    top, their direct reports nested underneath. Built in-memory from a
    single query rather than recursive SQL, since firm headcount is small
    enough that this is simpler and just as fast."""
    users = db.query(User).order_by(User.name).all()
    by_id = {u.id: u for u in users}
    children: dict[int | None, list[User]] = {}
    for u in users:
        children.setdefault(u.manager_id, []).append(u)

    def _node(user: User) -> dict:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "position": user.position,
            "department_id": user.department_id,
            "reports": [_node(child) for child in children.get(user.id, [])],
        }

    # Anyone whose manager_id points outside the loaded set (shouldn't
    # happen, but soft-deletes/edge cases exist) is also treated as a root.
    roots = [u for u in users if u.manager_id is None or u.manager_id not in by_id]
    return [_node(u) for u in roots]


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
