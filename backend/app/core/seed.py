from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User

DEMO_USERS = [
    {
        "name": "Admin User",
        "email": "admin@org.com",
        "role": "admin",
        "password": "Admin123!",
    },
    {
        "name": "Staff User",
        "email": "staff@org.com",
        "role": "staff",
        "password": "Staff123!",
    },
]

# Starting points for delegated permissions -- editable (including
# permissions and description) like any other role via app.routes.roles,
# just protected from deletion since a firm always benefits from having
# a sensible default to customize rather than build every role from
# scratch. Modeled on how authority is actually split at a professional
# services firm: a Partner carries broad delegated authority, a Manager
# handles day-to-day people management, and an Engagement Quality
# Reviewer has narrow but specific sign-off/override power over
# independence and workpaper review -- without any of them being able to
# create admin accounts or change anyone's system role.
DEFAULT_SYSTEM_ROLES = [
    {
        "name": "Partner",
        "description": "Broad delegated authority across the firm -- people management, leave approval, "
        "independence and workpaper overrides -- short of creating admin accounts or changing system roles.",
        "permissions": [
            "users.view",
            "users.manage",
            "users.manage_status",
            "departments.manage",
            "tags.manage",
            "leave.approve_any",
            "independence.override",
            "workpapers.override",
            "time_entries.manage_others",
            "content.moderate",
        ],
    },
    {
        "name": "Manager",
        "description": "Day-to-day people management: view the directory, approve leave for anyone, "
        "review others' time entries, and moderate client notes/comments.",
        "permissions": [
            "users.view",
            "leave.approve_any",
            "time_entries.manage_others",
            "content.moderate",
        ],
    },
    {
        "name": "Engagement Quality Reviewer",
        "description": "Narrow audit-quality authority: override independence conflicts and sign off "
        "on workpapers outside your assigned preparer/reviewer/partner role.",
        "permissions": [
            "independence.override",
            "workpapers.override",
        ],
    },
]


def seed_demo_users(db: Session) -> None:
    """Seed demo accounts on first run only. Never overwrites existing users,
    so passwords/roles changed later (or in production) are left untouched."""
    if db.query(User).count() > 0:
        return

    for demo in DEMO_USERS:
        db.add(
            User(
                name=demo["name"],
                email=demo["email"],
                role=demo["role"],
                disabled=False,
                hashed_password=get_password_hash(demo["password"]),
            )
        )

    db.commit()


def seed_default_roles(db: Session) -> None:
    """Seed the starting set of system roles on first run only. Runs
    independently of seed_demo_users -- gated on Role.count(), not
    User.count() -- so a firm that already has users but no roles yet
    (e.g. right after this feature ships) still gets the defaults."""
    if db.query(Role).count() > 0:
        return

    for defaults in DEFAULT_SYSTEM_ROLES:
        db.add(
            Role(
                name=defaults["name"],
                description=defaults["description"],
                permissions=defaults["permissions"],
                is_system=True,
            )
        )

    db.commit()
