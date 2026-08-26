from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.department_scope import department_id_for_project, require_scoped_write
from app.core.permissions import user_has_permission
from app.core.time import utcnow
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.workpaper import Workpaper, WorkpaperReviewEvent
from app.schemas.user import UserPublic
from app.schemas.workpaper import (
    WorkpaperCreate,
    WorkpaperOut,
    WorkpaperPartnerDecision,
    WorkpaperReviewDecision,
    WorkpaperReviewEventOut,
    WorkpaperSubmitRequest,
    WorkpaperUpdate,
)

router = APIRouter(prefix="/workpapers", tags=["Workpapers"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_DECISIONS = {"approved", "rejected"}


def _log_event(db: Session, workpaper: Workpaper, event_type: str, actor: UserPublic, notes: str | None):
    db.add(
        WorkpaperReviewEvent(
            workpaper_id=workpaper.id,
            event_type=event_type,
            notes=notes,
            actor_email=actor.email,
            actor_name=actor.name,
        )
    )


def _get_active_workpaper(db: Session, workpaper_id: int) -> Workpaper:
    workpaper = db.query(Workpaper).filter(Workpaper.id == workpaper_id, Workpaper.deleted_at.is_(None)).first()
    if not workpaper:
        raise HTTPException(status_code=404, detail="Workpaper not found")
    return workpaper


@router.get("/", response_model=list[WorkpaperOut])
def list_workpapers(
    response: Response,
    project_id: int | None = Query(default=None),
    stage: str | None = Query(default=None),
    category: str | None = Query(default=None),
    reviewer_id: int | None = Query(default=None),
    partner_id: int | None = Query(default=None),
    preparer_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Workpaper).filter(Workpaper.deleted_at.is_(None))

    if project_id is not None:
        query = query.filter(Workpaper.project_id == project_id)
    if stage:
        query = query.filter(Workpaper.stage == stage)
    if category:
        query = query.filter(Workpaper.category == category)
    if reviewer_id is not None:
        query = query.filter(Workpaper.reviewer_id == reviewer_id)
    if partner_id is not None:
        query = query.filter(Workpaper.partner_id == partner_id)
    if preparer_id is not None:
        query = query.filter(Workpaper.preparer_id == preparer_id)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(Workpaper.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=WorkpaperOut)
def create_workpaper(
    payload: WorkpaperCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    require_scoped_write(db, current_user, department_id_for_project(db, payload.project_id))

    preparer_id = payload.preparer_id or current_user.id
    preparer = db.query(User).filter(User.id == preparer_id).first()
    if not preparer:
        raise HTTPException(status_code=404, detail="Preparer not found")

    for label, uid in (("reviewer_id", payload.reviewer_id), ("partner_id", payload.partner_id)):
        if uid is not None and not db.query(User).filter(User.id == uid).first():
            raise HTTPException(status_code=404, detail=f"User referenced by {label} not found")

    workpaper = Workpaper(
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        file_id=payload.file_id,
        stage="in_preparation",
        preparer_id=preparer_id,
        prepared_by_email=preparer.email,
        prepared_by_name=preparer.name,
        reviewer_id=payload.reviewer_id,
        partner_id=payload.partner_id,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(workpaper)
    db.commit()
    db.refresh(workpaper)

    log_activity(
        db=db,
        user=current_user,
        action="workpaper_created",
        entity_type="workpaper",
        entity_id=workpaper.id,
        title=f"Workpaper created: {workpaper.name}",
        description=f"Added workpaper '{workpaper.name}' to engagement #{workpaper.project_id}.",
    )

    return workpaper


@router.get("/{workpaper_id}", response_model=WorkpaperOut)
def get_workpaper(
    workpaper_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return _get_active_workpaper(db, workpaper_id)


@router.get("/{workpaper_id}/events", response_model=list[WorkpaperReviewEventOut])
def list_workpaper_events(
    workpaper_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Full preparer -> reviewer -> partner history for this workpaper,
    including any rejection-and-rework rounds -- the current stage/status
    fields on the workpaper only show the latest round."""
    _get_active_workpaper(db, workpaper_id)
    return (
        db.query(WorkpaperReviewEvent)
        .filter(WorkpaperReviewEvent.workpaper_id == workpaper_id)
        .order_by(WorkpaperReviewEvent.created_at.asc())
        .all()
    )


@router.put("/{workpaper_id}", response_model=WorkpaperOut)
def update_workpaper(
    workpaper_id: int,
    payload: WorkpaperUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    workpaper = _get_active_workpaper(db, workpaper_id)
    require_scoped_write(db, current_user, department_id_for_project(db, workpaper.project_id))

    updates = payload.model_dump(exclude_unset=True)

    for label, field in (("reviewer_id", "reviewer_id"), ("partner_id", "partner_id")):
        uid = updates.get(field)
        if uid is not None and not db.query(User).filter(User.id == uid).first():
            raise HTTPException(status_code=404, detail=f"User referenced by {label} not found")

    for key, value in updates.items():
        setattr(workpaper, key, value)

    db.commit()
    db.refresh(workpaper)

    log_activity(
        db=db,
        user=current_user,
        action="workpaper_updated",
        entity_type="workpaper",
        entity_id=workpaper.id,
        title=f"Workpaper updated: {workpaper.name}",
        description="Workpaper record updated.",
    )

    return workpaper


@router.put("/{workpaper_id}/submit", response_model=WorkpaperOut)
def submit_for_review(
    workpaper_id: int,
    payload: WorkpaperSubmitRequest,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Preparer (or admin) moves a workpaper from in_preparation into the
    reviewer's queue. A reviewer must be assigned -- either already on the
    record or provided here -- since there's no one to route it to
    otherwise."""
    workpaper = _get_active_workpaper(db, workpaper_id)
    require_scoped_write(db, current_user, department_id_for_project(db, workpaper.project_id))

    if workpaper.stage != "in_preparation":
        raise HTTPException(
            status_code=400, detail=f"Workpaper must be in_preparation to submit for review (currently {workpaper.stage})"
        )

    if current_user.id != workpaper.preparer_id and not user_has_permission(db, current_user, "workpapers.override"):
        raise HTTPException(status_code=403, detail="Only the preparer or an admin can submit this workpaper for review")

    if payload.reviewer_id is not None:
        if not db.query(User).filter(User.id == payload.reviewer_id).first():
            raise HTTPException(status_code=404, detail="Reviewer not found")
        workpaper.reviewer_id = payload.reviewer_id

    if workpaper.reviewer_id is None:
        raise HTTPException(status_code=400, detail="A reviewer must be assigned before submitting for review")

    workpaper.stage = "pending_review"
    workpaper.submitted_for_review_at = utcnow()
    workpaper.review_status = None
    workpaper.reviewed_at = None
    workpaper.reviewed_by_email = None
    workpaper.reviewed_by_name = None
    workpaper.review_notes = None

    _log_event(db, workpaper, "submitted_for_review", current_user, payload.notes)
    db.commit()
    db.refresh(workpaper)

    log_activity(
        db=db,
        user=current_user,
        action="workpaper_submitted_for_review",
        entity_type="workpaper",
        entity_id=workpaper.id,
        title=f"Workpaper submitted for review: {workpaper.name}",
        description=f"'{workpaper.name}' submitted to reviewer #{workpaper.reviewer_id}.",
    )

    return workpaper


@router.put("/{workpaper_id}/review", response_model=WorkpaperOut)
def review_workpaper(
    workpaper_id: int,
    payload: WorkpaperReviewDecision,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """The assigned reviewer (or an admin) approves or rejects a workpaper
    that's pending review. Approval moves it to the partner's queue --
    which requires a partner to already be assigned, since approving into
    a void isn't useful. Rejection sends it back to the preparer."""
    workpaper = _get_active_workpaper(db, workpaper_id)
    require_scoped_write(db, current_user, department_id_for_project(db, workpaper.project_id))

    if workpaper.stage != "pending_review":
        raise HTTPException(
            status_code=400, detail=f"Workpaper must be pending_review to record a review decision (currently {workpaper.stage})"
        )

    if current_user.id != workpaper.reviewer_id and not user_has_permission(db, current_user, "workpapers.override"):
        raise HTTPException(status_code=403, detail="Only the assigned reviewer or an admin can review this workpaper")

    if payload.status not in VALID_DECISIONS:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_DECISIONS)}")

    workpaper.review_status = payload.status
    workpaper.reviewed_at = utcnow()
    workpaper.reviewed_by_email = current_user.email
    workpaper.reviewed_by_name = current_user.name
    workpaper.review_notes = payload.notes

    if payload.status == "approved":
        if workpaper.partner_id is None:
            raise HTTPException(
                status_code=400,
                detail="A partner must be assigned (PUT /workpapers/{id}) before this workpaper can move to partner sign-off",
            )
        workpaper.stage = "pending_partner_signoff"
        _log_event(db, workpaper, "review_approved", current_user, payload.notes)
    else:
        workpaper.stage = "in_preparation"
        workpaper.submitted_for_review_at = None
        _log_event(db, workpaper, "review_rejected", current_user, payload.notes)

    db.commit()
    db.refresh(workpaper)

    log_activity(
        db=db,
        user=current_user,
        action="workpaper_reviewed",
        entity_type="workpaper",
        entity_id=workpaper.id,
        title=f"Workpaper review {payload.status}: {workpaper.name}",
        description=f"Review of '{workpaper.name}' {payload.status}."
        + (f" Notes: {payload.notes}" if payload.notes else ""),
    )

    return workpaper


@router.put("/{workpaper_id}/partner-signoff", response_model=WorkpaperOut)
def partner_signoff(
    workpaper_id: int,
    payload: WorkpaperPartnerDecision,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """The assigned partner (or an admin) gives final sign-off on a
    workpaper that's cleared review. Approval completes the workpaper;
    rejection sends it all the way back to the preparer for rework, same
    as a review-stage rejection."""
    workpaper = _get_active_workpaper(db, workpaper_id)
    require_scoped_write(db, current_user, department_id_for_project(db, workpaper.project_id))

    if workpaper.stage != "pending_partner_signoff":
        raise HTTPException(
            status_code=400,
            detail=f"Workpaper must be pending_partner_signoff for partner sign-off (currently {workpaper.stage})",
        )

    if current_user.id != workpaper.partner_id and not user_has_permission(db, current_user, "workpapers.override"):
        raise HTTPException(status_code=403, detail="Only the assigned partner or an admin can sign off this workpaper")

    if payload.status not in VALID_DECISIONS:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_DECISIONS)}")

    workpaper.partner_status = payload.status
    workpaper.partner_by_email = current_user.email
    workpaper.partner_by_name = current_user.name
    workpaper.partner_notes = payload.notes

    if payload.status == "approved":
        workpaper.partner_signed_off_at = utcnow()
        workpaper.stage = "complete"
        _log_event(db, workpaper, "partner_approved", current_user, payload.notes)
    else:
        workpaper.partner_signed_off_at = None
        workpaper.stage = "in_preparation"
        workpaper.submitted_for_review_at = None
        workpaper.review_status = None
        workpaper.reviewed_at = None
        _log_event(db, workpaper, "partner_rejected", current_user, payload.notes)

    db.commit()
    db.refresh(workpaper)

    log_activity(
        db=db,
        user=current_user,
        action="workpaper_partner_signoff",
        entity_type="workpaper",
        entity_id=workpaper.id,
        title=f"Workpaper partner sign-off {payload.status}: {workpaper.name}",
        description=f"Partner sign-off on '{workpaper.name}' {payload.status}."
        + (f" Notes: {payload.notes}" if payload.notes else ""),
    )

    return workpaper


@router.delete("/{workpaper_id}")
def delete_workpaper(
    workpaper_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    workpaper = _get_active_workpaper(db, workpaper_id)
    require_scoped_write(db, current_user, department_id_for_project(db, workpaper.project_id))

    workpaper.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="workpaper_deleted",
        entity_type="workpaper",
        entity_id=workpaper_id,
        title=f"Workpaper deleted: {workpaper.name}",
        description=f"Workpaper #{workpaper_id} removed (soft delete).",
    )

    return {"message": "Workpaper deleted successfully"}
