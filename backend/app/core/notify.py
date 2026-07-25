from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify(
    db: Session,
    user_email: str | None,
    type: str,
    title: str,
    body: str = "",
    link: str | None = None,
) -> Notification | None:
    """Create an in-app notification for a user. No-op if user_email is
    empty (e.g. a task with nobody assigned yet)."""
    if not user_email:
        return None

    entry = Notification(
        user_email=user_email,
        type=type,
        title=title,
        body=body,
        link=link,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
