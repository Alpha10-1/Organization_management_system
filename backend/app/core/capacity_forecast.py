"""Rolling capacity forecast: for each staff member, project how much of
their standard weekly hours are already committed (via individual
ProjectAssignment.allocation_percent on planning/active engagements) across
each of the next N months, net of approved leave.

Department-wide assignments (ProjectAssignment.department_id set,
user_id null) are deliberately excluded from the numeric load calculation
-- they staff "the whole team" without a per-person split (allocation_percent
is rejected on them at creation, see app.routes.projects), so there's no
per-person hours figure to attribute. Only individual assignments carry
a real number to forecast against.

This is a heuristic planning tool, not a payroll/PTO system: month
boundaries are calendar months, a "week" is treated as a 5-day work week
for leave-hour conversion, and overlap is computed at day granularity.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.leave_request import LeaveRequest
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.models.user import User

# Engagement statuses that represent real, forecastable work. Completed and
# cancelled engagements no longer draw on anyone's time; on_hold is
# excluded too since the point of a forecast is upcoming committed work.
ACTIVE_PROJECT_STATUSES = ("planning", "active")

# allocated_percent below this is "bench" (meaningfully under-committed);
# above 100 is "overbooked". Between the two is "full" -- normal loading.
BENCH_THRESHOLD_PERCENT = 40
OVERBOOKED_THRESHOLD_PERCENT = 100

WORK_DAYS_PER_WEEK = Decimal(5)
DAYS_PER_WEEK = Decimal(7)


@dataclass
class MonthBucket:
    year: int
    month: int

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def start(self) -> date_type:
        return date_type(self.year, self.month, 1)

    @property
    def end(self) -> date_type:
        last_day = calendar.monthrange(self.year, self.month)[1]
        return date_type(self.year, self.month, last_day)

    @property
    def days_in_month(self) -> int:
        return (self.end - self.start).days + 1

    def next(self) -> "MonthBucket":
        if self.month == 12:
            return MonthBucket(self.year + 1, 1)
        return MonthBucket(self.year, self.month + 1)


def _month_buckets(start: date_type, months: int) -> list[MonthBucket]:
    bucket = MonthBucket(start.year, start.month)
    buckets = [bucket]
    for _ in range(months - 1):
        bucket = bucket.next()
        buckets.append(bucket)
    return buckets


def _overlap_days(
    range_start: date_type | None,
    range_end: date_type | None,
    bucket_start: date_type,
    bucket_end: date_type,
) -> int:
    """Days of overlap between an (open-ended-allowed) date range and a
    month bucket. A null start/end means "no bound in that direction" --
    an engagement with no end_date is treated as ongoing indefinitely, a
    leave request always has both bounds set."""

    effective_start = range_start if range_start is not None else bucket_start
    effective_end = range_end if range_end is not None else bucket_end

    latest_start = max(effective_start, bucket_start)
    earliest_end = min(effective_end, bucket_end)
    delta = (earliest_end - latest_start).days + 1
    return max(delta, 0)


@dataclass
class MonthForecast:
    month: str
    capacity_hours: Decimal
    leave_hours: Decimal
    allocated_percent: int
    allocated_hours: Decimal
    available_hours: Decimal
    status: str  # bench | full | overbooked
    project_names: list[str] = field(default_factory=list)


@dataclass
class UserForecast:
    user_id: int
    user_name: str
    department_id: int | None
    position: str | None
    standard_weekly_hours: Decimal
    months: list[MonthForecast]


def _weeks_in_bucket(bucket: MonthBucket) -> Decimal:
    return Decimal(bucket.days_in_month) / DAYS_PER_WEEK


def _leave_hours_for_bucket(
    leave_requests: list[LeaveRequest], bucket: MonthBucket, weekly_hours: Decimal
) -> Decimal:
    daily_hours = weekly_hours / WORK_DAYS_PER_WEEK
    total_days = 0
    for leave in leave_requests:
        total_days += _overlap_days(leave.start_date, leave.end_date, bucket.start, bucket.end)
    return daily_hours * Decimal(total_days)


def compute_user_forecast(
    db: Session,
    user: User,
    months: int = 12,
    start: date_type | None = None,
) -> UserForecast:
    start = start or date_type.today()
    buckets = _month_buckets(start, months)
    weekly_hours = Decimal(str(user.standard_weekly_hours or 40))

    assignments = (
        db.query(ProjectAssignment, Project)
        .join(Project, Project.id == ProjectAssignment.project_id)
        .filter(
            ProjectAssignment.user_id == user.id,
            Project.deleted_at.is_(None),
            Project.status.in_(ACTIVE_PROJECT_STATUSES),
        )
        .all()
    )

    leave_requests = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == "approved",
            LeaveRequest.deleted_at.is_(None),
        )
        .all()
    )

    month_forecasts: list[MonthForecast] = []
    for bucket in buckets:
        weeks = _weeks_in_bucket(bucket)
        full_capacity_hours = weekly_hours * weeks
        leave_hours = _leave_hours_for_bucket(leave_requests, bucket, weekly_hours)
        capacity_hours = max(full_capacity_hours - leave_hours, Decimal(0))

        allocated_percent = 0
        project_names: list[str] = []
        for assignment, project in assignments:
            overlap = _overlap_days(project.start_date and project.start_date.date(), project.end_date and project.end_date.date(), bucket.start, bucket.end)
            if overlap <= 0:
                continue
            # An assignment only counts toward this month if the
            # engagement is actually running during it -- allocation_percent
            # is the *while active* commitment, not spread evenly across
            # the engagement's whole lifetime.
            allocated_percent += assignment.allocation_percent or 0
            project_names.append(project.name)

        allocated_hours = full_capacity_hours * (Decimal(allocated_percent) / Decimal(100))
        available_hours = capacity_hours - allocated_hours

        if allocated_percent > OVERBOOKED_THRESHOLD_PERCENT:
            status = "overbooked"
        elif allocated_percent < BENCH_THRESHOLD_PERCENT:
            status = "bench"
        else:
            status = "full"

        month_forecasts.append(
            MonthForecast(
                month=bucket.label,
                capacity_hours=capacity_hours.quantize(Decimal("0.01")),
                leave_hours=leave_hours.quantize(Decimal("0.01")),
                allocated_percent=allocated_percent,
                allocated_hours=allocated_hours.quantize(Decimal("0.01")),
                available_hours=available_hours.quantize(Decimal("0.01")),
                status=status,
                project_names=project_names,
            )
        )

    return UserForecast(
        user_id=user.id,
        user_name=user.name,
        department_id=user.department_id,
        position=user.position,
        standard_weekly_hours=weekly_hours,
        months=month_forecasts,
    )


def compute_firm_forecast(
    db: Session,
    months: int = 12,
    department_id: int | None = None,
    user_id: int | None = None,
    start: date_type | None = None,
) -> list[UserForecast]:
    query = db.query(User).filter(User.disabled.is_(False))
    if department_id is not None:
        query = query.filter(User.department_id == department_id)
    if user_id is not None:
        query = query.filter(User.id == user_id)

    users = query.order_by(User.name.asc()).all()
    return [compute_user_forecast(db, user, months=months, start=start) for user in users]
