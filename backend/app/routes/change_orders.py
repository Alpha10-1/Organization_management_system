from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.department_scope import department_id_for_contract, require_scoped_write
from app.core.time import utcnow
from app.db.session import get_db
from app.models.change_order import ChangeOrder
from app.models.contract import Contract
from app.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderDecision,
    ChangeOrderOut,
    ChangeOrderUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/change-orders", tags=["Change Orders"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_CHANGE_TYPES = {"fee_increase", "fee_decrease", "scope_change", "other"}
VALID_STATUSES = {"pending", "approved", "rejected"}


def _validate_amount_sign(change_type: str, amount_delta: Decimal | None):
    if amount_delta is None:
        return
    if change_type == "fee_increase" and amount_delta <= 0:
        raise HTTPException(status_code=400, detail="amount_delta must be positive for a fee_increase")
    if change_type == "fee_decrease" and amount_delta >= 0:
        raise HTTPException(status_code=400, detail="amount_delta must be negative for a fee_decrease")


@router.get("/", response_model=list[ChangeOrderOut])
def list_change_orders(
    response: Response,
    project_id: int | None = Query(default=None),
    contract_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(ChangeOrder).filter(ChangeOrder.deleted_at.is_(None))

    if project_id is not None:
        query = query.filter(ChangeOrder.project_id == project_id)
    if contract_id is not None:
        query = query.filter(ChangeOrder.contract_id == contract_id)
    if status:
        query = query.filter(ChangeOrder.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(ChangeOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ChangeOrderOut)
def create_change_order(
    payload: ChangeOrderCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.change_type not in VALID_CHANGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid change_type. Must be one of: {sorted(VALID_CHANGE_TYPES)}")

    contract = db.query(Contract).filter(Contract.id == payload.contract_id, Contract.deleted_at.is_(None)).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    require_scoped_write(db, current_user, department_id_for_contract(db, contract.id))

    _validate_amount_sign(payload.change_type, payload.amount_delta)

    change_order = ChangeOrder(
        **payload.model_dump(),
        project_id=contract.project_id,
        status="pending",
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(change_order)
    db.commit()
    db.refresh(change_order)

    log_activity(
        db=db,
        user=current_user,
        action="change_order_created",
        entity_type="change_order",
        entity_id=change_order.id,
        title=f"Change order requested: {change_order.title}",
        description=f"Requested change order '{change_order.title}' against contract '{contract.name}'.",
    )

    return change_order


@router.get("/{change_order_id}", response_model=ChangeOrderOut)
def get_change_order(
    change_order_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    change_order = (
        db.query(ChangeOrder).filter(ChangeOrder.id == change_order_id, ChangeOrder.deleted_at.is_(None)).first()
    )
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")
    return change_order


@router.put("/{change_order_id}", response_model=ChangeOrderOut)
def update_change_order(
    change_order_id: int,
    payload: ChangeOrderUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    change_order = (
        db.query(ChangeOrder).filter(ChangeOrder.id == change_order_id, ChangeOrder.deleted_at.is_(None)).first()
    )
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")
    if change_order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending change orders can be edited")

    require_scoped_write(db, current_user, department_id_for_contract(db, change_order.contract_id))

    updates = payload.model_dump(exclude_unset=True)
    if "change_type" in updates and updates["change_type"] not in VALID_CHANGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid change_type. Must be one of: {sorted(VALID_CHANGE_TYPES)}")

    new_type = updates.get("change_type", change_order.change_type)
    new_amount = updates.get("amount_delta", change_order.amount_delta)
    _validate_amount_sign(new_type, new_amount)

    for key, value in updates.items():
        setattr(change_order, key, value)

    db.commit()
    db.refresh(change_order)
    return change_order


@router.post("/{change_order_id}/approve", response_model=ChangeOrderOut)
def approve_change_order(
    change_order_id: int,
    payload: ChangeOrderDecision = ChangeOrderDecision(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Approving applies amount_delta to the contract's value, preserving
    the change order itself as the audit trail for why the value moved."""
    change_order = (
        db.query(ChangeOrder).filter(ChangeOrder.id == change_order_id, ChangeOrder.deleted_at.is_(None)).first()
    )
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")
    if change_order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending change orders can be approved")

    contract = db.query(Contract).filter(Contract.id == change_order.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    require_scoped_write(db, current_user, department_id_for_contract(db, change_order.contract_id))

    if change_order.amount_delta is not None:
        contract.value = (contract.value or Decimal("0")) + change_order.amount_delta

    change_order.status = "approved"
    change_order.decided_at = utcnow()
    change_order.decided_by_email = current_user.email
    change_order.decided_by_name = current_user.name

    db.commit()
    db.refresh(change_order)

    log_activity(
        db=db,
        user=current_user,
        action="change_order_approved",
        entity_type="change_order",
        entity_id=change_order.id,
        title=f"Change order approved: {change_order.title}",
        description=(
            f"Approved '{change_order.title}' against contract '{contract.name}'."
            + (f" Contract value adjusted by {change_order.amount_delta}." if change_order.amount_delta else "")
        ),
    )

    return change_order


@router.post("/{change_order_id}/reject", response_model=ChangeOrderOut)
def reject_change_order(
    change_order_id: int,
    payload: ChangeOrderDecision = ChangeOrderDecision(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    change_order = (
        db.query(ChangeOrder).filter(ChangeOrder.id == change_order_id, ChangeOrder.deleted_at.is_(None)).first()
    )
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")
    if change_order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending change orders can be rejected")

    require_scoped_write(db, current_user, department_id_for_contract(db, change_order.contract_id))

    change_order.status = "rejected"
    change_order.decided_at = utcnow()
    change_order.decided_by_email = current_user.email
    change_order.decided_by_name = current_user.name

    db.commit()
    db.refresh(change_order)

    log_activity(
        db=db,
        user=current_user,
        action="change_order_rejected",
        entity_type="change_order",
        entity_id=change_order.id,
        title=f"Change order rejected: {change_order.title}",
        description=f"Rejected '{change_order.title}'." + (f" Reason: {payload.reason}" if payload.reason else ""),
    )

    return change_order


@router.delete("/{change_order_id}")
def delete_change_order(
    change_order_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    change_order = (
        db.query(ChangeOrder).filter(ChangeOrder.id == change_order_id, ChangeOrder.deleted_at.is_(None)).first()
    )
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")

    require_scoped_write(db, current_user, department_id_for_contract(db, change_order.contract_id))

    change_order.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="change_order_deleted",
        entity_type="change_order",
        entity_id=change_order_id,
        title=f"Change order deleted: {change_order.title}",
        description="Change order removed (soft delete).",
    )

    return {"message": "Change order deleted successfully"}
