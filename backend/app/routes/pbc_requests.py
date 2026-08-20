from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.department_scope import department_id_for_project, require_scoped_write
from app.core.email import send_email
from app.core.time import utcnow
from app.db.session import get_db
from app.models.pbc_request import PBCRequest
from app.models.project import Project
from app.schemas.pbc_request import (
    PBCRequestCreate,
    PBCRequestOut,
    PBCRequestReview,
    PBCRequestUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/pbc-requests", tags=["PBC Requests"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_REVIEW_STATUSES = {"approved", "rejected"}


@router.get("/", response_model=list[PBCRequestOut])
def list_pbc_requests(
    response: Response,
    project_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(PBCRequest).filter(PBCRequest.deleted_at.is_(None))

    if project_id is not None:
        query = query.filter(PBCRequest.project_id == project_id)
    if status:
        query = query.filter(PBCRequest.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return (
        query.order_by(PBCRequest.due_date.is_(None), PBCRequest.due_date.asc(), PBCRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=PBCRequestOut)
def create_pbc_request(
    payload: PBCRequestCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    require_scoped_write(db, current_user, department_id_for_project(db, payload.project_id))

    pbc_request = PBCRequest(
        **payload.model_dump(),
        requested_by_email=current_user.email,
        requested_by_name=current_user.name,
    )
    db.add(pbc_request)
    db.commit()
    db.refresh(pbc_request)

    log_activity(
        db=db,
        user=current_user,
        action="pbc_request_created",
        entity_type="pbc_request",
        entity_id=pbc_request.id,
        title=f"PBC request added: {pbc_request.title}",
        description=f"Requested '{pbc_request.title}' from the client on engagement #{pbc_request.project_id}.",
    )

    return pbc_request


@router.get("/{pbc_request_id}", response_model=PBCRequestOut)
def get_pbc_request(
    pbc_request_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    pbc_request = (
        db.query(PBCRequest)
        .filter(PBCRequest.id == pbc_request_id, PBCRequest.deleted_at.is_(None))
        .first()
    )
    if not pbc_request:
        raise HTTPException(status_code=404, detail="PBC request not found")
    return pbc_request


@router.put("/{pbc_request_id}", response_model=PBCRequestOut)
def update_pbc_request(
    pbc_request_id: int,
    payload: PBCRequestUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    pbc_request = (
        db.query(PBCRequest)
        .filter(PBCRequest.id == pbc_request_id, PBCRequest.deleted_at.is_(None))
        .first()
    )
    if not pbc_request:
        raise HTTPException(status_code=404, detail="PBC request not found")

    require_scoped_write(db, current_user, department_id_for_project(db, pbc_request.project_id))

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(pbc_request, key, value)

    db.commit()
    db.refresh(pbc_request)

    log_activity(
        db=db,
        user=current_user,
        action="pbc_request_updated",
        entity_type="pbc_request",
        entity_id=pbc_request.id,
        title=f"PBC request updated: {pbc_request.title}",
        description="PBC request details updated.",
    )

    return pbc_request


@router.put("/{pbc_request_id}/review", response_model=PBCRequestOut)
def review_pbc_request(
    pbc_request_id: int,
    payload: PBCRequestReview,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Staff review of a client's submission: approve it, or reject it and
    send it back to the client (status returns to "requested" so it
    reappears as outstanding in the portal, with review_notes explaining
    what's needed instead)."""
    pbc_request = (
        db.query(PBCRequest)
        .filter(PBCRequest.id == pbc_request_id, PBCRequest.deleted_at.is_(None))
        .first()
    )
    if not pbc_request:
        raise HTTPException(status_code=404, detail="PBC request not found")

    require_scoped_write(db, current_user, department_id_for_project(db, pbc_request.project_id))

    if payload.status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_REVIEW_STATUSES)}")

    if pbc_request.status != "submitted":
        raise HTTPException(status_code=400, detail="Only a submitted PBC request can be reviewed")

    pbc_request.reviewed_at = utcnow()
    pbc_request.reviewed_by_email = current_user.email
    pbc_request.reviewed_by_name = current_user.name
    pbc_request.review_notes = payload.notes

    if payload.status == "approved":
        pbc_request.status = "approved"
    else:
        # Rejected submissions go back to "requested" (not a dead-end
        # "rejected" status) so the client's portal view keeps surfacing
        # it as outstanding work rather than requiring a separate
        # re-request from staff.
        pbc_request.status = "requested"

    db.commit()
    db.refresh(pbc_request)

    if pbc_request.submitted_by_email:
        # The client can't read in-app notifications (those are a
        # staff-only surface -- see routes/notifications.py), so the
        # outcome is emailed instead, same zero-cost channel used for
        # portal invites and password resets.
        if payload.status == "approved":
            body = f"Your submission for '{pbc_request.title}' has been reviewed and approved. No further action needed."
        else:
            body = (
                f"Your submission for '{pbc_request.title}' needs another look before it can be accepted.\n\n"
                f"Notes from the reviewer: {payload.notes or '(none provided)'}\n\n"
                "Please log back into the client portal to upload a revised document."
            )
        send_email(
            db=db,
            to_email=pbc_request.submitted_by_email,
            subject=f"Update on your document request: {pbc_request.title}",
            body=body,
            kind="pbc_review",
        )

    log_activity(
        db=db,
        user=current_user,
        action="pbc_request_reviewed",
        entity_type="pbc_request",
        entity_id=pbc_request.id,
        title=f"PBC request {payload.status}: {pbc_request.title}",
        description=payload.notes or "",
    )

    return pbc_request


@router.delete("/{pbc_request_id}")
def delete_pbc_request(
    pbc_request_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    pbc_request = (
        db.query(PBCRequest)
        .filter(PBCRequest.id == pbc_request_id, PBCRequest.deleted_at.is_(None))
        .first()
    )
    if not pbc_request:
        raise HTTPException(status_code=404, detail="PBC request not found")

    require_scoped_write(db, current_user, department_id_for_project(db, pbc_request.project_id))

    pbc_request.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="pbc_request_deleted",
        entity_type="pbc_request",
        entity_id=pbc_request_id,
        title=f"PBC request deleted: {pbc_request.title}",
        description="",
    )

    return {"message": "PBC request deleted"}
