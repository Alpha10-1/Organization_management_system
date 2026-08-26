"""Delegated-permission resolution for custom Roles (see app.models.role).

Admin always has every permission, unconditionally -- a custom role only
ever adds capability to a "staff" user, never restricts an admin. This
mirrors how department scoping (app.core.department_scope) and
department management (app.core.deps.require_department_manage) both
already treat admin as an unconditional bypass; permissions here are
just another axis of the same pattern, not a replacement for it.

The permission catalog is deliberately scoped to specific, previously
admin-only actions across the app (see each key's description) rather
than being a general-purpose ACL framework -- it grants exactly the
slices of admin authority a real firm would want to delegate to a
Partner, Manager, or similar, and nothing that would let a delegated
role manage roles/permissions itself or change another user's system
role (admin/staff), both of which stay hard-coded admin-only regardless
of what any custom role grants.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserPublic

PERMISSION_CATALOG: dict[str, str] = {
    "users.view": "View the full user directory and org chart",
    "users.manage": "Create users and edit profile fields (position, department, billing rate, weekly hours)",
    "users.manage_status": "Enable or disable a user account",
    "departments.manage": "Create and delete departments",
    "tags.manage": "Edit and delete tags",
    "leave.approve_any": "View, approve, reject, or cancel any staff member's leave request",
    "independence.override": (
        "View all independence disclosures, log one on someone else's behalf, "
        "and override an independence conflict when staffing an engagement"
    ),
    "workpapers.override": "Submit, review, or sign off a workpaper outside your assigned preparer/reviewer/partner role",
    "time_entries.manage_others": "View and edit other staff members' time entries",
    "content.moderate": "Edit or delete another user's client notes and comments",
}


def validate_permission_keys(keys: list[str]) -> None:
    unknown = sorted(set(keys) - set(PERMISSION_CATALOG))
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown permission key(s): {', '.join(unknown)}. "
            f"See GET /roles/catalog for valid keys.",
        )


def get_user_permissions(db: Session, user_id: int) -> set[str]:
    """The resolved set of permission keys for a user -- empty for admins
    (who don't need permission keys, they bypass every check) and for
    staff with no custom role assigned."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.custom_role_id:
        return set()

    role = db.query(Role).filter(Role.id == user.custom_role_id, Role.deleted_at.is_(None)).first()
    if not role:
        return set()

    return set(role.permissions or [])


def user_has_permission(db: Session, current_user: UserPublic, permission_key: str) -> bool:
    if current_user.role == "admin":
        return True
    return permission_key in get_user_permissions(db, current_user.id)


def require_permission(permission_key: str):
    """FastAPI dependency: admin always passes; otherwise the caller's
    assigned custom role must include this permission key. Use this in
    place of require_role("admin") for any action that's reasonable to
    delegate -- see PERMISSION_CATALOG for what's already wired up."""

    async def checker(
        db: Session = Depends(get_db),
        current_user: UserPublic = Depends(get_current_active_user),
    ) -> UserPublic:
        if not user_has_permission(db, current_user, permission_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have the '{permission_key}' permission required for this action",
            )
        return current_user

    return checker
