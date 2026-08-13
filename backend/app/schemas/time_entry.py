from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class TimeEntryBase(BaseModel):
    project_id: int
    task_id: Optional[int] = None
    hours: Decimal
    entry_date: date
    billable: bool = True
    notes: Optional[str] = None
    # Only admins/managers may set this to log time on someone else's
    # behalf; when omitted the current user is used (see routes).
    user_email: Optional[EmailStr] = None

    @field_validator("hours")
    @classmethod
    def hours_in_range(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("hours must be greater than 0")
        if v > 24:
            raise ValueError("hours cannot exceed 24 for a single entry")
        return v


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    hours: Optional[Decimal] = None
    entry_date: Optional[date] = None
    billable: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("hours")
    @classmethod
    def hours_in_range(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v <= 0:
            raise ValueError("hours must be greater than 0")
        if v > 24:
            raise ValueError("hours cannot exceed 24 for a single entry")
        return v


class TimeEntryOut(BaseModel):
    id: int
    project_id: int
    task_id: Optional[int] = None
    user_email: str
    user_name: str
    hours: Decimal
    entry_date: date
    billable: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectUtilization(BaseModel):
    """Rolled-up hours for a single project, the feed for margin/utilization
    dashboards described in the reporting feature."""

    project_id: int
    total_hours: Decimal
    billable_hours: Decimal
    non_billable_hours: Decimal
    budget: Optional[Decimal] = None
    entry_count: int
