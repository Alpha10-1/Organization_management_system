from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ContractBase(BaseModel):
    project_id: int
    name: str
    billing_type: str = "fixed_fee"
    value: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    signed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str = "draft"
    notes: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    billing_type: Optional[str] = None
    value: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    signed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ContractOut(BaseModel):
    id: int
    project_id: int
    name: str
    billing_type: str
    value: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    signed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractMargin(BaseModel):
    """Contract value vs. hours logged, the lightweight margin-visibility
    view described in the brief (no full invoicing needed)."""

    contract_id: int
    project_id: int
    billing_type: str
    contract_value: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    billable_hours: Decimal
    non_billable_hours: Decimal
    hours_value: Optional[Decimal] = None  # billable_hours * hourly_rate, when hourly_rate is set
    remaining_value: Optional[Decimal] = None  # contract_value - hours_value, when both are set
