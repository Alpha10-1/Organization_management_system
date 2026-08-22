from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class CapacityMonthOut(BaseModel):
    month: str  # "YYYY-MM"
    capacity_hours: Decimal
    leave_hours: Decimal
    allocated_percent: int
    allocated_hours: Decimal
    available_hours: Decimal
    status: str  # bench | full | overbooked
    project_names: list[str]


class UserCapacityForecastOut(BaseModel):
    user_id: int
    user_name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    position: Optional[str] = None
    standard_weekly_hours: Decimal
    months: list[CapacityMonthOut]


class CapacityMonthSummaryOut(BaseModel):
    month: str
    overbooked_count: int
    bench_count: int
    overbooked_users: list[str]
    bench_users: list[str]


class CapacityForecastSummaryOut(BaseModel):
    months: list[CapacityMonthSummaryOut]
