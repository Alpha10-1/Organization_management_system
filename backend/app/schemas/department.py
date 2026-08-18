from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    department_head_user_id: Optional[int] = None
    annual_budget: Optional[Decimal] = None
    cost_center_code: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_head_user_id: Optional[int] = None
    annual_budget: Optional[Decimal] = None
    cost_center_code: Optional[str] = None


class DepartmentOut(DepartmentBase):
    id: int
    department_head_user_id: Optional[int] = None
    annual_budget: Optional[Decimal] = None
    cost_center_code: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentDashboard(BaseModel):
    """Department-level read layer: utilization, active engagement count,
    average risk level, and revenue -- the same pattern as the firm-wide
    capacity dashboard, scoped to one department."""

    department_id: int
    department_name: str
    cost_center_code: Optional[str] = None
    annual_budget: Optional[Decimal] = None
    staff_count: int
    average_allocated_percent: float
    over_allocated_count: int
    under_allocated_count: int
    bench_count: int
    active_engagement_count: int
    average_risk_level: Optional[str] = None
    revenue_to_date: Decimal
    budget_variance: Optional[Decimal] = None  # revenue_to_date - annual_budget, when annual_budget is set
