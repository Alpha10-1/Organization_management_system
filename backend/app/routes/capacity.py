from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.capacity_forecast import compute_firm_forecast
from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.department import Department
from app.schemas.capacity import (
    CapacityForecastSummaryOut,
    CapacityMonthOut,
    CapacityMonthSummaryOut,
    UserCapacityForecastOut,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/capacity", tags=["Capacity Forecasting"])


@router.get("/forecast", response_model=list[UserCapacityForecastOut])
def get_capacity_forecast(
    months: int = Query(default=12, ge=1, le=24),
    department_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    start_date: date_type | None = Query(
        default=None, description="First month of the forecast; defaults to the current month."
    ),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Rolling per-person capacity forecast: for each of the next `months`
    calendar months, how many hours each active staff member is expected
    to have committed (via allocation_percent on planning/active
    engagements) versus available, net of approved leave. This is the
    forward-looking companion to /reports/dashboard/capacity, which only
    reports current-moment allocation with no time dimension.
    """
    if department_id is not None:
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")

    forecasts = compute_firm_forecast(
        db, months=months, department_id=department_id, user_id=user_id, start=start_date
    )

    dept_names: dict[int, str] = {}
    if forecasts:
        dept_ids = {f.department_id for f in forecasts if f.department_id is not None}
        if dept_ids:
            for dept in db.query(Department).filter(Department.id.in_(dept_ids)).all():
                dept_names[dept.id] = dept.name

    return [
        UserCapacityForecastOut(
            user_id=f.user_id,
            user_name=f.user_name,
            department_id=f.department_id,
            department_name=dept_names.get(f.department_id) if f.department_id else None,
            position=f.position,
            standard_weekly_hours=f.standard_weekly_hours,
            months=[
                CapacityMonthOut(
                    month=m.month,
                    capacity_hours=m.capacity_hours,
                    leave_hours=m.leave_hours,
                    allocated_percent=m.allocated_percent,
                    allocated_hours=m.allocated_hours,
                    available_hours=m.available_hours,
                    status=m.status,
                    project_names=m.project_names,
                )
                for m in f.months
            ],
        )
        for f in forecasts
    ]


@router.get("/forecast/summary", response_model=CapacityForecastSummaryOut)
def get_capacity_forecast_summary(
    months: int = Query(default=12, ge=1, le=24),
    department_id: int | None = Query(default=None),
    start_date: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Firm-wide (or department-scoped) rollup: for each forecasted month,
    who's overbooked (busy-season staffing risk) and who's on the bench
    (a hiring/utilization signal), month by month across the whole
    horizon rather than just today.
    """
    forecasts = compute_firm_forecast(db, months=months, department_id=department_id, start=start_date)

    month_labels: list[str] = [m.month for m in forecasts[0].months] if forecasts else []

    months_out: list[CapacityMonthSummaryOut] = []
    for i, label in enumerate(month_labels):
        overbooked = [f.user_name for f in forecasts if f.months[i].status == "overbooked"]
        bench = [f.user_name for f in forecasts if f.months[i].status == "bench"]
        months_out.append(
            CapacityMonthSummaryOut(
                month=label,
                overbooked_count=len(overbooked),
                bench_count=len(bench),
                overbooked_users=overbooked,
                bench_users=bench,
            )
        )

    return CapacityForecastSummaryOut(months=months_out)
