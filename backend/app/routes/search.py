from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.core.engagement_search import search_engagements
from app.db.session import get_db
from app.models.client import Client
from app.models.file_record import FileRecord
from app.models.task import Task
from app.models.user import User
from app.schemas.user import UserPublic

router = APIRouter(prefix="/search", tags=["Search"])

RESULT_LIMIT_PER_TYPE = 8


@router.get("/")
def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    term = f"%{q}%"

    clients = (
        db.query(Client)
        .filter(
            Client.deleted_at.is_(None),
            or_(
                Client.first_name.ilike(term),
                Client.last_name.ilike(term),
                Client.company_name.ilike(term),
                Client.email.ilike(term),
                Client.phone.ilike(term),
            ),
        )
        .limit(RESULT_LIMIT_PER_TYPE)
        .all()
    )

    files = (
        db.query(FileRecord)
        .filter(FileRecord.deleted_at.is_(None), FileRecord.original_name.ilike(term))
        .limit(RESULT_LIMIT_PER_TYPE)
        .all()
    )

    tasks = (
        db.query(Task)
        .filter(
            Task.deleted_at.is_(None),
            or_(Task.title.ilike(term), Task.description.ilike(term)),
        )
        .limit(RESULT_LIMIT_PER_TYPE)
        .all()
    )

    results = {
        "clients": [
            {
                "id": c.id,
                "label": c.display_name,
                "subtitle": c.email or c.phone or c.status,
                "link": f"/dashboard/clients?client_id={c.id}",
            }
            for c in clients
        ],
        "files": [
            {
                "id": f.id,
                "label": f.original_name,
                "subtitle": f.file_type or "",
                "link": f"/dashboard/files?file_id={f.id}",
            }
            for f in files
        ],
        "tasks": [
            {
                "id": t.id,
                "label": t.title,
                "subtitle": t.status,
                "link": f"/dashboard/tasks?task_id={t.id}",
            }
            for t in tasks
        ],
    }

    if current_user.role == "admin":
        users = (
            db.query(User)
            .filter(or_(User.name.ilike(term), User.email.ilike(term)))
            .limit(RESULT_LIMIT_PER_TYPE)
            .all()
        )
        results["users"] = [
            {
                "id": u.id,
                "label": u.name,
                "subtitle": u.email,
                "link": "/dashboard/users",
            }
            for u in users
        ]

    return results


@router.get("/engagements")
def search_engagements_nl(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Plain-language search over an engagement's narrative history --
    project notes/objectives/close-out notes, its client's notes, and its
    own activity log -- rather than the exact-name matching global_search
    above does. E.g. "show me every engagement where we flagged a going
    concern issue" matches on the phrase "going concern" wherever it
    appears in that history."""
    return search_engagements(db, q)
