"""Computes budget-burn (logged cost vs. engagement budget) for a project.
Kept separate from routes so both the project budget endpoint and the
engagement health score can reuse the same logic without duplicating it."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.project import Project
from app.models.time_entry import TimeEntry

DEFAULT_ALERT_THRESHOLD_PERCENT = 80.0


def _effective_hourly_rate(db: Session, project_id: int) -> Decimal | None:
    """Picks a representative hourly rate to translate logged hours into a
    dollar cost. Prefers a signed hourly contract (most recently created);
    falls back to any contract on the engagement that has a rate set, since
    even a draft/sent rate is better signal than nothing."""
    contracts = (
        db.query(Contract)
        .filter(Contract.project_id == project_id, Contract.deleted_at.is_(None), Contract.hourly_rate.isnot(None))
        .order_by(Contract.created_at.desc())
        .all()
    )
    if not contracts:
        return None

    for contract in contracts:
        if contract.status == "signed" and contract.billing_type == "hourly":
            return contract.hourly_rate
    for contract in contracts:
        if contract.billing_type == "hourly":
            return contract.hourly_rate
    return contracts[0].hourly_rate


def compute_budget_burn(db: Session, project: Project, alert_threshold_percent: float = DEFAULT_ALERT_THRESHOLD_PERCENT) -> dict:
    base_query = db.query(TimeEntry).filter(TimeEntry.project_id == project.id, TimeEntry.deleted_at.is_(None))

    billable_hours = base_query.filter(TimeEntry.billable.is_(True)).all()
    non_billable_hours = base_query.filter(TimeEntry.billable.is_(False)).all()

    total_billable = sum((Decimal(str(e.hours)) for e in billable_hours), Decimal("0"))
    total_non_billable = sum((Decimal(str(e.hours)) for e in non_billable_hours), Decimal("0"))

    hourly_rate = _effective_hourly_rate(db, project.id)
    cost_to_date = total_billable * hourly_rate if hourly_rate is not None else None

    percent_consumed = None
    if cost_to_date is not None and project.budget is not None and project.budget > 0:
        percent_consumed = float(cost_to_date / project.budget * 100)

    if project.budget is None:
        status = "no_budget"
    elif cost_to_date is None:
        status = "hours_only"
    elif percent_consumed >= 100:
        status = "over_budget"
    elif percent_consumed >= alert_threshold_percent:
        status = "at_risk"
    else:
        status = "on_track"

    return {
        "project_id": project.id,
        "budget": project.budget,
        "billable_hours": total_billable,
        "non_billable_hours": total_non_billable,
        "effective_hourly_rate": hourly_rate,
        "cost_to_date": cost_to_date,
        "percent_consumed": percent_consumed,
        "alert_threshold_percent": alert_threshold_percent,
        "alert": status in ("over_budget", "at_risk"),
        "status": status,
    }
