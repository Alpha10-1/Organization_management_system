from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.department_scope import department_id_for_project, require_scoped_write
from app.core.time import utcnow
from app.db.session import get_db
from app.models.milestone import Milestone
from app.models.project import Project
from app.schemas.milestone import (
    MilestoneCreate,
    MilestoneOut,
    MilestoneSignoffRequest,
    MilestoneUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/milestones", tags=["Milestones"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_STATUSES = {"pending", "achieved", "missed"}
VALID_APPROVAL_STATUSES = {"pending", "approved", "rejected"}


@router.get("/", response_model=list[MilestoneOut])
def list_milestones(
    response: Response,
    project_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Milestone).filter(Milestone.deleted_at.is_(None))

    if project_id is not None:
        query = query.filter(Milestone.project_id == project_id)
    if status:
        query = query.filter(Milestone.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return (
        query.order_by(Milestone.due_date.is_(None), Milestone.due_date.asc(), Milestone.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=MilestoneOut)
def create_milestone(
    payload: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")

    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    require_scoped_write(db, current_user, department_id_for_project(db, payload.project_id))

    milestone = Milestone(
        **payload.model_dump(),
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    log_activity(
        db=db,
        user=current_user,
        action="milestone_created",
        entity_type="milestone",
        entity_id=milestone.id,
        title=f"Milestone created: {milestone.name}",
        description=f"Added milestone '{milestone.name}' to engagement #{milestone.project_id}.",
    )

    return milestone


@router.get("/{milestone_id}", response_model=MilestoneOut)
def get_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.deleted_at.is_(None)).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.put("/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: int,
    payload: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.deleted_at.is_(None)).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    require_scoped_write(db, current_user, department_id_for_project(db, milestone.project_id))

    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")

    for key, value in updates.items():
        setattr(milestone, key, value)

    if updates.get("status") == "achieved" and milestone.achieved_at is None:
        milestone.achieved_at = utcnow()
    elif updates.get("status") is not None and updates.get("status") != "achieved":
        milestone.achieved_at = None

    db.commit()
    db.refresh(milestone)

    log_activity(
        db=db,
        user=current_user,
        action="milestone_updated",
        entity_type="milestone",
        entity_id=milestone.id,
        title=f"Milestone updated: {milestone.name}",
        description="Milestone record updated.",
    )

    return milestone


@router.put("/{milestone_id}/signoff", response_model=MilestoneOut)
def signoff_milestone(
    milestone_id: int,
    payload: MilestoneSignoffRequest,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Lightweight client acknowledgment status for a milestone/deliverable,
    tracked separately from the internal `status` field above -- useful for
    engagement types where client sign-off matters (audit findings, tax
    filings) without forcing every milestone through the workflow."""
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.deleted_at.is_(None)).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    require_scoped_write(db, current_user, department_id_for_project(db, milestone.project_id))

    if payload.status not in VALID_APPROVAL_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_APPROVAL_STATUSES)}"
        )

    milestone.approval_status = payload.status
    if payload.status == "approved":
        milestone.approved_at = utcnow()
        milestone.approved_by_email = current_user.email
        milestone.approved_by_name = current_user.name
        milestone.rejection_reason = None
    elif payload.status == "rejected":
        milestone.approved_at = None
        milestone.approved_by_email = current_user.email
        milestone.approved_by_name = current_user.name
        milestone.rejection_reason = payload.reason
    else:  # pending
        milestone.approved_at = None
        milestone.rejection_reason = None

    db.commit()
    db.refresh(milestone)

    log_activity(
        db=db,
        user=current_user,
        action="milestone_signoff_updated",
        entity_type="milestone",
        entity_id=milestone.id,
        title=f"Milestone sign-off {payload.status}: {milestone.name}",
        description=f"Client sign-off on '{milestone.name}' set to '{payload.status}'."
        + (f" Reason: {payload.reason}" if payload.status == "rejected" and payload.reason else ""),
    )

    return milestone


@router.delete("/{milestone_id}")
def delete_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.deleted_at.is_(None)).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    require_scoped_write(db, current_user, department_id_for_project(db, milestone.project_id))

    milestone.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="milestone_deleted",
        entity_type="milestone",
        entity_id=milestone_id,
        title=f"Milestone deleted: {milestone.name}",
        description="Milestone removed (soft delete).",
    )

    return {"message": "Milestone deleted successfully"}
