from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ChangeOrderBase(BaseModel):
    contract_id: int
    title: str
    description: Optional[str] = None
    change_type: str = "scope_change"
    amount_delta: Optional[Decimal] = None
    hours_delta: Optional[Decimal] = None
    requested_date: Optional[date] = None


class ChangeOrderCreate(ChangeOrderBase):
    pass


class ChangeOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    change_type: Optional[str] = None
    amount_delta: Optional[Decimal] = None
    hours_delta: Optional[Decimal] = None
    requested_date: Optional[date] = None


class ChangeOrderDecision(BaseModel):
    reason: Optional[str] = None


class ChangeOrderOut(BaseModel):
    id: int
    contract_id: int
    project_id: int
    title: str
    description: Optional[str] = None
    change_type: str
    amount_delta: Optional[Decimal] = None
    hours_delta: Optional[Decimal] = None
    status: str
    requested_date: Optional[date] = None
    decided_at: Optional[datetime] = None
    decided_by_email: Optional[str] = None
    decided_by_name: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
