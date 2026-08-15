from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr


class ProjectBase(BaseModel):
    name: str
    client_id: int
    type: str = "other"
    status: str = "planning"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[Decimal] = None
    engagement_partner_email: Optional[EmailStr] = None
    engagement_manager_email: Optional[EmailStr] = None
    description: Optional[str] = None
    risk_level: str = "low"
    compliance_flag: Optional[str] = None

    # Optional extended detail ("Specify More" section on the form).
    objectives: Optional[str] = None
    deliverables: Optional[str] = None
    stakeholders: Optional[str] = None
    billing_notes: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client_id: Optional[int] = None
    type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[Decimal] = None
    engagement_partner_email: Optional[EmailStr] = None
    engagement_manager_email: Optional[EmailStr] = None
    description: Optional[str] = None
    risk_level: Optional[str] = None
    compliance_flag: Optional[str] = None
    objectives: Optional[str] = None
    deliverables: Optional[str] = None
    stakeholders: Optional[str] = None
    billing_notes: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    client_id: int
    name: str
    type: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[Decimal] = None
    engagement_partner_email: Optional[str] = None
    engagement_partner_name: Optional[str] = None
    engagement_manager_email: Optional[str] = None
    engagement_manager_name: Optional[str] = None
    description: Optional[str] = None
    risk_level: str
    compliance_flag: Optional[str] = None
    objectives: Optional[str] = None
    deliverables: Optional[str] = None
    stakeholders: Optional[str] = None
    billing_notes: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(ProjectOut):
    """Project with rolled-up task counts, used on list/detail views so the
    frontend doesn't need a second round-trip per project."""

    task_count: int = 0
    open_task_count: int = 0
    overdue_task_count: int = 0
