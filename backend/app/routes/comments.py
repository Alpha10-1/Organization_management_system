import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_user_by_email
from app.core.notify import notify
from app.core.time import utcnow
from app.db.session import get_db
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/comments", tags=["Comments"])

MENTION_PATTERN = re.compile(r"@([\w.+-]+@[\w-]+\.[\w.-]+)")


@router.get("/", response_model=list[CommentOut])
def list_comments(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return (
        db.query(Comment)
        .filter(
            Comment.entity_type == entity_type,
            Comment.entity_id == entity_id,
            Comment.deleted_at.is_(None),
        )
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.post("/", response_model=CommentOut)
def create_comment(
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    mentioned_emails = {email.lower() for email in MENTION_PATTERN.findall(payload.body)}

    comment = Comment(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        author_email=current_user.email,
        author_name=current_user.name,
        body=payload.body,
        mentions=",".join(sorted(mentioned_emails)) if mentioned_emails else None,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    for email in mentioned_emails:
        if email == current_user.email:
            continue
        if not get_user_by_email(db, email):
            continue
        notify(
            db=db,
            user_email=email,
            type="mention",
            title=f"{current_user.name} mentioned you",
            body=payload.body[:200],
            link=f"/dashboard?entity_type={payload.entity_type}&entity_id={payload.entity_id}",
        )

    return comment


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.deleted_at.is_(None)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.author_email != current_user.email and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only delete your own comments")

    comment.deleted_at = utcnow()
    db.commit()
    return {"message": "Comment deleted"}
