from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResourceRequestBase(BaseModel):
    requesting_department_id: int
    providing_department_id: int
    project_id: int
    requested_user_id: Optional[int] = None
    role_needed: Optional[str] = None
    allocation_percent: Optional[int] = Field(default=None, ge=1, le=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class ResourceRequestCreate(ResourceRequestBase):
    pass


class ResourceRequestDecision(BaseModel):
    notes: Optional[str] = None


class ResourceRequestOut(BaseModel):
    id: int
    requesting_department_id: int
    providing_department_id: int
    project_id: int
    requested_user_id: Optional[int] = None
    role_needed: Optional[str] = None
    allocation_percent: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    status: str
    decided_at: Optional[datetime] = None
    decided_by_email: Optional[str] = None
    decided_by_name: Optional[str] = None
    requested_by_email: str
    requested_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
