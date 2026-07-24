from sqlalchemy.orm import Session

from app.core.security import get_password_hash
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
