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
    close_out_notes: Optional[str] = None


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
    close_out_notes: Optional[str] = None


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
    close_out_notes: Optional[str] = None
    cloned_from_project_id: Optional[int] = None
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


class ProjectBudgetBurn(BaseModel):
    """Logged cost vs. engagement budget, so burn can be seen proactively
    as the engagement runs rather than only at contract margin time."""

    project_id: int
    budget: Optional[Decimal] = None
    billable_hours: Decimal
    non_billable_hours: Decimal
    effective_hourly_rate: Optional[Decimal] = None
    cost_to_date: Optional[Decimal] = None
    percent_consumed: Optional[float] = None
    alert_threshold_percent: float
    alert: bool
    status: str  # no_budget | hours_only | on_track | at_risk | over_budget


class ProjectHealth(BaseModel):
    """Rolled-up partner-level signal for an engagement: overdue tasks,
    budget burn, risk level, and timeline slippage folded into one
    green/amber/red indicator, the same pattern as client relationship
    health but scoped per engagement."""

    project_id: int
    health: str  # green | amber | red
    reasons: list[str]
    overdue_task_count: int
    missed_milestone_count: int
    risk_level: str
    budget_status: str
    percent_budget_consumed: Optional[float] = None
    timeline_slipped: bool


class ProjectCloneRequest(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_team: bool = True
    include_milestones: bool = True
    include_tasks: bool = False


class ProjectCloneResult(BaseModel):
    project: ProjectOut
    milestones_cloned: int
    assignments_cloned: int
    tasks_cloned: int
