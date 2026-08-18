from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, is_department_manager
from app.core.department_scope import require_scoped_write
from app.core.time import utcnow
from app.db.session import get_db
from app.models.department import Department
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.models.resource_request import ResourceRequest
from app.models.user import User
from app.schemas.resource_request import (
    ResourceRequestCreate,
    ResourceRequestDecision,
    ResourceRequestOut,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/resource-requests", tags=["Resource Requests"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_STATUSES = {"pending", "approved", "rejected", "cancelled"}


def _require_provider_manage(db: Session, current_user: UserPublic, providing_department_id: int) -> None:
    """Only the providing department's head (who's being asked to lend
    staff) or an admin can approve/reject -- the requesting department
    doesn't get to unilaterally grant itself someone else's staff."""
    if current_user.role == "admin":
        return
    if is_department_manager(db, current_user.id, providing_department_id):
        return
    raise HTTPException(
        status_code=403,
        detail="Only the providing department's head or an admin can decide this request",
    )


@router.get("/", response_model=list[ResourceRequestOut])
def list_resource_requests(
    response: Response,
    requesting_department_id: int | None = Query(default=None),
    providing_department_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(ResourceRequest).filter(ResourceRequest.deleted_at.is_(None))

    if requesting_department_id is not None:
        query = query.filter(ResourceRequest.requesting_department_id == requesting_department_id)
    if providing_department_id is not None:
        query = query.filter(ResourceRequest.providing_department_id == providing_department_id)
    if project_id is not None:
        query = query.filter(ResourceRequest.project_id == project_id)
    if status:
        query = query.filter(ResourceRequest.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(ResourceRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ResourceRequestOut)
def create_resource_request(
    payload: ResourceRequestCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.requesting_department_id == payload.providing_department_id:
        raise HTTPException(status_code=400, detail="requesting_department_id and providing_department_id must differ")

    requesting_dept = db.query(Department).filter(Department.id == payload.requesting_department_id).first()
    if not requesting_dept:
        raise HTTPException(status_code=404, detail="Requesting department not found")
    providing_dept = db.query(Department).filter(Department.id == payload.providing_department_id).first()
    if not providing_dept:
        raise HTTPException(status_code=404, detail="Providing department not found")

    require_scoped_write(db, current_user, payload.requesting_department_id)

    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.requested_user_id is not None:
        requested_user = db.query(User).filter(User.id == payload.requested_user_id).first()
        if not requested_user:
            raise HTTPException(status_code=404, detail="Requested user not found")
        if requested_user.department_id != payload.providing_department_id:
            raise HTTPException(
                status_code=400, detail="Requested user does not belong to the providing department"
            )

    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    request = ResourceRequest(
        **payload.model_dump(),
        status="pending",
        requested_by_email=current_user.email,
        requested_by_name=current_user.name,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    log_activity(
        db=db,
        user=current_user,
        action="resource_request_created",
        entity_type="resource_request",
        entity_id=request.id,
        title=f"Resource request: {requesting_dept.name} -> {providing_dept.name}",
        description=f"Requested staff from '{providing_dept.name}' for engagement '{project.name}'.",
    )

    return request


@router.get("/{request_id}", response_model=ResourceRequestOut)
def get_resource_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    request = (
        db.query(ResourceRequest)
        .filter(ResourceRequest.id == request_id, ResourceRequest.deleted_at.is_(None))
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Resource request not found")
    return request


@router.post("/{request_id}/approve", response_model=ResourceRequestOut)
def approve_resource_request(
    request_id: int,
    payload: ResourceRequestDecision = ResourceRequestDecision(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Approving loans the staff member onto the engagement via a normal
    ProjectAssignment, without changing their department_id -- they're
    borrowed, not moved."""
    request = (
        db.query(ResourceRequest)
        .filter(ResourceRequest.id == request_id, ResourceRequest.deleted_at.is_(None))
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Resource request not found")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")

    _require_provider_manage(db, current_user, request.providing_department_id)

    if request.requested_user_id is not None:
        existing = (
            db.query(ProjectAssignment)
            .filter(
                ProjectAssignment.project_id == request.project_id,
                ProjectAssignment.user_id == request.requested_user_id,
            )
            .first()
        )
        if not existing:
            db.add(
                ProjectAssignment(
                    project_id=request.project_id,
                    user_id=request.requested_user_id,
                    role=request.role_needed,
                    allocation_percent=request.allocation_percent,
                    assigned_by_email=current_user.email,
                    assigned_by_name=current_user.name,
                )
            )

    request.status = "approved"
    request.decided_at = utcnow()
    request.decided_by_email = current_user.email
    request.decided_by_name = current_user.name
    if payload.notes:
        request.notes = f"{request.notes}\n---\n{payload.notes}" if request.notes else payload.notes

    db.commit()
    db.refresh(request)

    log_activity(
        db=db,
        user=current_user,
        action="resource_request_approved",
        entity_type="resource_request",
        entity_id=request.id,
        title="Resource request approved",
        description=f"Approved loan onto engagement #{request.project_id}.",
    )

    return request


@router.post("/{request_id}/reject", response_model=ResourceRequestOut)
def reject_resource_request(
    request_id: int,
    payload: ResourceRequestDecision = ResourceRequestDecision(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    request = (
        db.query(ResourceRequest)
        .filter(ResourceRequest.id == request_id, ResourceRequest.deleted_at.is_(None))
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Resource request not found")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")

    _require_provider_manage(db, current_user, request.providing_department_id)

    request.status = "rejected"
    request.decided_at = utcnow()
    request.decided_by_email = current_user.email
    request.decided_by_name = current_user.name
    if payload.notes:
        request.notes = f"{request.notes}\n---\n{payload.notes}" if request.notes else payload.notes

    db.commit()
    db.refresh(request)
    return request


@router.delete("/{request_id}")
def cancel_resource_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    request = (
        db.query(ResourceRequest)
        .filter(ResourceRequest.id == request_id, ResourceRequest.deleted_at.is_(None))
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Resource request not found")

    request.status = "cancelled"
    request.deleted_at = utcnow()
    db.commit()
    return {"message": "Resource request cancelled successfully"}
