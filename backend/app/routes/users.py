from fastapi import APIRouter, Depends, HTTPException, status

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, require_role
from app.core.fake_db import fake_users_db, get_next_user_id
from app.core.security import get_password_hash
from app.db.session import get_db
from app.schemas.user import UserPublic
from app.schemas.user_management import (
    UserCreate,
    UserManagementOut,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserManagementOut])
def list_users(
    current_user: UserPublic = Depends(require_role("admin")),
):
    users = []
    for user in fake_users_db.values():
        users.append(
            UserManagementOut(
                id=user["id"],
                name=user["name"],
                email=user["email"],
                role=user["role"],
                disabled=user["disabled"],
            )
        )
    return sorted(users, key=lambda u: u.id)


@router.post("/", response_model=UserManagementOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    email = payload.email.lower()

    if email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    if payload.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    user = {
        "id": get_next_user_id(),
        "name": payload.name,
        "email": email,
        "role": payload.role,
        "disabled": False,
        "hashed_password": get_password_hash(payload.password),
    }

    fake_users_db[email] = user

    log_activity(
        db=db,
        user=current_user,
        action="user_created",
        entity_type="user",
        entity_id=user["id"],
        title=f"User created: {user['name']}",
        description=f"Created user '{user['email']}' with role '{user['role']}'.",
    )

    return UserManagementOut(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        disabled=user["disabled"],
    )


@router.put("/{email}", response_model=UserManagementOut)
def update_user(
    email: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = fake_users_db.get(email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        target["name"] = payload.name

    if payload.role is not None:
        if payload.role not in ["admin", "staff"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        target["role"] = payload.role

    if payload.disabled is not None:
        target["disabled"] = payload.disabled

    log_activity(
        db=db,
        user=current_user,
        action="user_updated",
        entity_type="user",
        entity_id=target["id"],
        title=f"User updated: {target['name']}",
        description=f"Updated user '{target['email']}'.",
    )

    return UserManagementOut(
        id=target["id"],
        name=target["name"],
        email=target["email"],
        role=target["role"],
        disabled=target["disabled"],
    )


@router.patch("/{email}/role", response_model=UserManagementOut)
def update_user_role(
    email: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = fake_users_db.get(email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role not in ["admin", "staff"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    target["role"] = payload.role

    log_activity(
        db=db,
        user=current_user,
        action="user_role_updated",
        entity_type="user",
        entity_id=target["id"],
        title=f"User role changed: {target['name']}",
        description=f"Changed role to '{target['role']}' for '{target['email']}'.",
    )

    return UserManagementOut(
        id=target["id"],
        name=target["name"],
        email=target["email"],
        role=target["role"],
        disabled=target["disabled"],
    )


@router.patch("/{email}/status", response_model=UserManagementOut)
def update_user_status(
    email: str,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    target = fake_users_db.get(email.lower())

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target["disabled"] = payload.disabled

    log_activity(
        db=db,
        user=current_user,
        action="user_status_updated",
        entity_type="user",
        entity_id=target["id"],
        title=f"User status changed: {target['name']}",
        description=f"Set disabled={target['disabled']} for '{target['email']}'.",
    )

    return UserManagementOut(
        id=target["id"],
        name=target["name"],
        email=target["email"],
        role=target["role"],
        disabled=target["disabled"],
    )