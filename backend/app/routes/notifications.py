from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Notification).filter(Notification.user_email == current_user.email)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    return query.order_by(Notification.created_at.desc()).limit(limit).all()


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    count = (
        db.query(Notification)
        .filter(Notification.user_email == current_user.email, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_email == current_user.email)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()
    return {"message": "Marked as read"}


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    (
        db.query(Notification)
        .filter(Notification.user_email == current_user.email, Notification.is_read.is_(False))
        .update({Notification.is_read: True})
    )
    db.commit()
    return {"message": "All notifications marked as read"}
