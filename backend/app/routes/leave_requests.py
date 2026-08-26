from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.permissions import user_has_permission
from app.core.time import utcnow
from app.db.session import get_db
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestDecision, LeaveRequestOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/leave-requests", tags=["Leave Requests"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_LEAVE_TYPES = {"pto", "sick", "unpaid", "other"}


@router.get("/", response_model=list[LeaveRequestOut])
def list_leave_requests(
    response: Response,
    user_id: int | None = Query(default=None),
    approver_user_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Defaults to the caller's own requests plus anything routed to them
    for approval, so a manager's queue and a staff member's own history
    both work without extra filters -- explicit user_id/approver_user_id
    override this for admin/browsing use."""
    query = db.query(LeaveRequest).filter(LeaveRequest.deleted_at.is_(None))

    if user_id is not None:
        query = query.filter(LeaveRequest.user_id == user_id)
    if approver_user_id is not None:
        query = query.filter(LeaveRequest.approver_user_id == approver_user_id)
    if user_id is None and approver_user_id is None and not user_has_permission(db, current_user, "leave.approve_any"):
        query = query.filter(
            (LeaveRequest.user_id == current_user.id) | (LeaveRequest.approver_user_id == current_user.id)
        )
    if status:
        query = query.filter(LeaveRequest.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(LeaveRequest.start_date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=LeaveRequestOut)
def create_leave_request(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.leave_type not in VALID_LEAVE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid leave_type. Must be one of: {sorted(VALID_LEAVE_TYPES)}")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    requester = db.query(User).filter(User.id == current_user.id).first()
    if not requester.manager_id:
        raise HTTPException(
            status_code=400, detail="You have no manager on file, so this request has no one to route to"
        )

    request = LeaveRequest(
        user_id=requester.id,
        approver_user_id=requester.manager_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status="pending",
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    log_activity(
        db=db,
        user=current_user,
        action="leave_request_created",
        entity_type="leave_request",
        entity_id=request.id,
        title=f"Leave requested: {requester.name}",
        description=f"{requester.name} requested {payload.leave_type} leave from {payload.start_date} to {payload.end_date}.",
    )

    return request


@router.get("/{request_id}", response_model=LeaveRequestOut)
def get_leave_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    request = db.query(LeaveRequest).filter(LeaveRequest.id == request_id, LeaveRequest.deleted_at.is_(None)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return request


def _require_approver(db: Session, current_user: UserPublic, request: LeaveRequest) -> None:
    if current_user.id != request.approver_user_id and not user_has_permission(db, current_user, "leave.approve_any"):
        raise HTTPException(status_code=403, detail="Only this request's approver or an admin can decide it")


@router.post("/{request_id}/approve", response_model=LeaveRequestOut)
def approve_leave_request(
    request_id: int,
    payload: LeaveRequestDecision = LeaveRequestDecision(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    request = db.query(LeaveRequest).filter(LeaveRequest.id == request_id, LeaveRequest.deleted_at.is_(None)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")

    _require_approver(db, current_user, request)

    request.status = "approved"
    request.decided_at = utcnow()
    request.decided_by_email = current_user.email
    request.decided_by_name = current_user.name
    request.decision_notes = payload.notes

    db.commit()
    db.refresh(request)

    log_activity(
        db=db,
        user=current_user,
        action="leave_request_approved",
        entity_type="leave_request",
        entity_id=request.id,
        title="Leave request approved",
        description=f"Approved leave for user #{request.user_id} ({request.start_date} to {request.end_date}).",
    )

    return request


@router.post("/{request_id}/reject", response_model=LeaveRequestOut)
def reject_leave_request(
    request_id: int,
    payload: LeaveRequestDecision = LeaveRequestDecision(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    request = db.query(LeaveRequest).filter(LeaveRequest.id == request_id, LeaveRequest.deleted_at.is_(None)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")

    _require_approver(db, current_user, request)

    request.status = "rejected"
    request.decided_at = utcnow()
    request.decided_by_email = current_user.email
    request.decided_by_name = current_user.name
    request.decision_notes = payload.notes

    db.commit()
    db.refresh(request)
    return request


@router.delete("/{request_id}")
def cancel_leave_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """The requester can cancel their own pending request; an admin can
    cancel any."""
    request = db.query(LeaveRequest).filter(LeaveRequest.id == request_id, LeaveRequest.deleted_at.is_(None)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if current_user.id != request.user_id and not user_has_permission(db, current_user, "leave.approve_any"):
        raise HTTPException(status_code=403, detail="Only the requester or an admin can cancel this request")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")

    request.status = "cancelled"
    request.deleted_at = utcnow()
    db.commit()
    return {"message": "Leave request cancelled successfully"}
