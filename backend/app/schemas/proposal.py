from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProposalCreate(BaseModel):
    prospect_id: int
    title: str
    scope_summary: Optional[str] = None
    proposed_value: Optional[Decimal] = None
    sent_date: Optional[date_type] = None
    valid_until: Optional[date_type] = None
    notes: Optional[str] = None


class ProposalUpdate(BaseModel):
    title: Optional[str] = None
    scope_summary: Optional[str] = None
    proposed_value: Optional[Decimal] = None
    sent_date: Optional[date_type] = None
    valid_until: Optional[date_type] = None
    notes: Optional[str] = None


class ProposalStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ProposalOut(BaseModel):
    id: int
    prospect_id: int
    title: str
    scope_summary: Optional[str] = None
    proposed_value: Optional[Decimal] = None
    status: str
    sent_date: Optional[date_type] = None
    valid_until: Optional[date_type] = None
    decided_at: Optional[datetime] = None
    decided_by_email: Optional[str] = None
    decided_by_name: Optional[str] = None
    decision_notes: Optional[str] = None
    notes: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
