from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, get_user_by_email
from app.core.permissions import user_has_permission
from app.core.time import utcnow
from app.core.time_anomaly import detect_time_entry_anomalies
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.time_entry import TimeEntry
from app.schemas.time_anomaly import TimeEntryAnomalyOut
from app.schemas.time_entry import (
    ProjectUtilization,
    TimeEntryCreate,
    TimeEntryOut,
    TimeEntryUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/time-entries", tags=["Time Tracking"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 500

# Admins, or a staff member with the delegated "time_entries.manage_others"
# permission, may log time on someone else's behalf or view/edit their
# entries.
def _can_manage_others_time(db: Session, current_user: UserPublic) -> bool:
    return user_has_permission(db, current_user, "time_entries.manage_others")


def _resolve_owner(db: Session, payload_email: str | None, current_user: UserPublic) -> tuple[str, str]:
    if not payload_email or payload_email.lower() == current_user.email.lower():
        return current_user.email, current_user.name

    if not _can_manage_others_time(db, current_user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to log time on behalf of another user",
        )

    owner = get_user_by_email(db, payload_email.lower())
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")
    return owner.email, owner.name


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _validate_task_belongs_to_project(db: Session, task_id: int, project_id: int) -> None:
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.project_id is not None and task.project_id != project_id:
        raise HTTPException(status_code=400, detail="task does not belong to the given project")


@router.get("/", response_model=list[TimeEntryOut])
def list_time_entries(
    response: Response,
    project_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    user_email: str | None = Query(default=None),
    billable: bool | None = Query(default=None),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(TimeEntry).filter(TimeEntry.deleted_at.is_(None))

    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    if task_id is not None:
        query = query.filter(TimeEntry.task_id == task_id)
    if user_email:
        query = query.filter(TimeEntry.user_email == user_email.lower())
    if billable is not None:
        query = query.filter(TimeEntry.billable == billable)
    if date_from is not None:
        query = query.filter(TimeEntry.entry_date >= date_from)
    if date_to is not None:
        query = query.filter(TimeEntry.entry_date <= date_to)

    response.headers["X-Total-Count"] = str(query.count())

    return (
        query.order_by(TimeEntry.entry_date.desc(), TimeEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=TimeEntryOut)
def create_time_entry(
    payload: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    _get_project_or_404(db, payload.project_id)

    if payload.task_id is not None:
        _validate_task_belongs_to_project(db, payload.task_id, payload.project_id)

    owner_email, owner_name = _resolve_owner(db, payload.user_email, current_user)

    entry = TimeEntry(
        project_id=payload.project_id,
        task_id=payload.task_id,
        user_email=owner_email,
        user_name=owner_name,
        hours=payload.hours,
        entry_date=payload.entry_date,
        billable=payload.billable,
        notes=payload.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    log_activity(
        db=db,
        user=current_user,
        action="time_entry_logged",
        entity_type="time_entry",
        entity_id=entry.id,
        title=f"{entry.hours}h logged on project #{entry.project_id}",
        description=f"{owner_name} logged {entry.hours}h ({'billable' if entry.billable else 'non-billable'}).",
    )

    return entry


@router.get("/summary", response_model=ProjectUtilization)
def project_utilization(
    project_id: int = Query(...),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = _get_project_or_404(db, project_id)

    query = db.query(TimeEntry).filter(TimeEntry.project_id == project_id, TimeEntry.deleted_at.is_(None))
    if date_from is not None:
        query = query.filter(TimeEntry.entry_date >= date_from)
    if date_to is not None:
        query = query.filter(TimeEntry.entry_date <= date_to)

    total_hours = query.with_entities(func.coalesce(func.sum(TimeEntry.hours), 0)).scalar()
    billable_hours = (
        query.filter(TimeEntry.billable.is_(True))
        .with_entities(func.coalesce(func.sum(TimeEntry.hours), 0))
        .scalar()
    )
    entry_count = query.count()

    total_hours = Decimal(total_hours)
    billable_hours = Decimal(billable_hours)

    return ProjectUtilization(
        project_id=project_id,
        total_hours=total_hours,
        billable_hours=billable_hours,
        non_billable_hours=total_hours - billable_hours,
        budget=project.budget,
        entry_count=entry_count,
    )


@router.get("/anomalies", response_model=list[TimeEntryAnomalyOut])
def list_time_entry_anomalies(
    project_id: int | None = Query(default=None),
    user_email: str | None = Query(default=None),
    since: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Rules-based flags over logged time entries (late-logged, large
    Friday blocks, possible duplicates, round-number repeat patterns) --
    for partner review and audit-quality controls, not an accusation
    engine. Non-admins are limited to their own entries; admins can filter
    by any project/user."""
    if not _can_manage_others_time(db, current_user) and (
        user_email is None or user_email.lower() != current_user.email.lower()
    ):
        user_email = current_user.email

    if project_id is not None:
        _get_project_or_404(db, project_id)

    return detect_time_entry_anomalies(db, project_id=project_id, user_email=user_email, since=since)


@router.get("/{entry_id}", response_model=TimeEntryOut)
def get_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id, TimeEntry.deleted_at.is_(None)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return entry


@router.put("/{entry_id}", response_model=TimeEntryOut)
def update_time_entry(
    entry_id: int,
    payload: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id, TimeEntry.deleted_at.is_(None)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    if entry.user_email != current_user.email and not _can_manage_others_time(db, current_user):
        raise HTTPException(status_code=403, detail="You can only edit your own time entries")

    updates = payload.model_dump(exclude_unset=True)

    new_project_id = updates.get("project_id", entry.project_id)
    if "project_id" in updates:
        _get_project_or_404(db, new_project_id)

    new_task_id = updates.get("task_id", entry.task_id)
    if new_task_id is not None and ("task_id" in updates or "project_id" in updates):
        _validate_task_belongs_to_project(db, new_task_id, new_project_id)

    for key, value in updates.items():
        setattr(entry, key, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}")
def delete_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id, TimeEntry.deleted_at.is_(None)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    if entry.user_email != current_user.email and not _can_manage_others_time(db, current_user):
        raise HTTPException(status_code=403, detail="You can only delete your own time entries")

    entry.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="time_entry_deleted",
        entity_type="time_entry",
        entity_id=entry_id,
        title=f"Time entry deleted on project #{entry.project_id}",
        description="Time entry removed (soft delete).",
    )

    return {"message": "Time entry deleted successfully"}
