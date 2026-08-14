from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.time import utcnow
from app.db.session import get_db
from app.models.contract import Contract
from app.models.project import Project
from app.models.time_entry import TimeEntry
from app.schemas.contract import ContractCreate, ContractMargin, ContractOut, ContractUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/contracts", tags=["Contracts"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_BILLING_TYPES = {"fixed_fee", "hourly", "retainer"}
VALID_STATUSES = {"draft", "sent", "signed", "expired", "terminated"}


@router.get("/", response_model=list[ContractOut])
def list_contracts(
    response: Response,
    project_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    billing_type: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Contract).filter(Contract.deleted_at.is_(None))

    if project_id is not None:
        query = query.filter(Contract.project_id == project_id)
    if status:
        query = query.filter(Contract.status == status)
    if billing_type:
        query = query.filter(Contract.billing_type == billing_type)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ContractOut)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.billing_type not in VALID_BILLING_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid billing_type. Must be one of: {sorted(VALID_BILLING_TYPES)}")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")

    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.signed_date and payload.expiry_date and payload.expiry_date < payload.signed_date:
        raise HTTPException(status_code=400, detail="expiry_date cannot be before signed_date")

    contract = Contract(
        **payload.model_dump(),
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    log_activity(
        db=db,
        user=current_user,
        action="contract_created",
        entity_type="contract",
        entity_id=contract.id,
        title=f"Contract created: {contract.name}",
        description=f"Created {contract.billing_type} contract '{contract.name}' for engagement #{contract.project_id}.",
    )

    return contract


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.deleted_at.is_(None)).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.put("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: int,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.deleted_at.is_(None)).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    updates = payload.model_dump(exclude_unset=True)

    if "billing_type" in updates and updates["billing_type"] not in VALID_BILLING_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid billing_type. Must be one of: {sorted(VALID_BILLING_TYPES)}")
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")

    new_signed = updates.get("signed_date", contract.signed_date)
    new_expiry = updates.get("expiry_date", contract.expiry_date)
    if new_signed and new_expiry and new_expiry < new_signed:
        raise HTTPException(status_code=400, detail="expiry_date cannot be before signed_date")

    for key, value in updates.items():
        setattr(contract, key, value)

    db.commit()
    db.refresh(contract)

    log_activity(
        db=db,
        user=current_user,
        action="contract_updated",
        entity_type="contract",
        entity_id=contract.id,
        title=f"Contract updated: {contract.name}",
        description="Contract record updated.",
    )

    return contract


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.deleted_at.is_(None)).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    contract.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="contract_deleted",
        entity_type="contract",
        entity_id=contract_id,
        title=f"Contract deleted: {contract.name}",
        description="Contract removed (soft delete).",
    )

    return {"message": "Contract deleted successfully"}


@router.get("/{contract_id}/margin", response_model=ContractMargin)
def get_contract_margin(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Contract value vs. hours logged on its engagement -- the lightweight
    margin-visibility view described in the brief, without full invoicing."""
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.deleted_at.is_(None)).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    base_query = db.query(TimeEntry).filter(TimeEntry.project_id == contract.project_id, TimeEntry.deleted_at.is_(None))
    billable_hours = (
        base_query.filter(TimeEntry.billable.is_(True))
        .with_entities(func.coalesce(func.sum(TimeEntry.hours), 0))
        .scalar()
    )
    non_billable_hours = (
        base_query.filter(TimeEntry.billable.is_(False))
        .with_entities(func.coalesce(func.sum(TimeEntry.hours), 0))
        .scalar()
    )

    billable_hours = Decimal(str(billable_hours))
    non_billable_hours = Decimal(str(non_billable_hours))

    hours_value = None
    remaining_value = None
    if contract.hourly_rate is not None:
        hours_value = billable_hours * contract.hourly_rate
        if contract.value is not None:
            remaining_value = contract.value - hours_value

    return ContractMargin(
        contract_id=contract.id,
        project_id=contract.project_id,
        billing_type=contract.billing_type,
        contract_value=contract.value,
        hourly_rate=contract.hourly_rate,
        billable_hours=billable_hours,
        non_billable_hours=non_billable_hours,
        hours_value=hours_value,
        remaining_value=remaining_value,
    )
