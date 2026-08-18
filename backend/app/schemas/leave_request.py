from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class LeaveRequestCreate(BaseModel):
    leave_type: str = "pto"
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestDecision(BaseModel):
    notes: Optional[str] = None


class LeaveRequestOut(BaseModel):
    id: int
    user_id: int
    approver_user_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str] = None
    status: str
    decided_at: Optional[datetime] = None
    decided_by_email: Optional[str] = None
    decided_by_name: Optional[str] = None
    decision_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
