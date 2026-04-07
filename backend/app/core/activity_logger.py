from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.schemas.user import UserPublic


def log_activity(
    db: Session,
    user: UserPublic,
    action: str,
    entity_type: str,
    title: str,
    description: str = "",
    entity_id: int | None = None,
):
    entry = ActivityLog(
        user_email=user.email,
        user_name=user.name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        description=description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry