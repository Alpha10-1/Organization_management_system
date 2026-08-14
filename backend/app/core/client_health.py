"""Computes a green/amber/red relationship-health signal for a client by
rolling up overdue tasks, contract renewal proximity, and open engagement
counts. Kept separate from the routes module so both the client detail
endpoint and partner-level dashboards can reuse the same logic."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.contract import Contract
from app.models.project import Project
from app.models.task import Task

VALID_HEALTH_VALUES = {"green", "amber", "red"}
CONTRACT_RENEWAL_WARNING_DAYS = 30


def compute_client_health(db: Session, client_id: int) -> dict:
    now = utcnow()

    overdue_task_count = (
        db.query(Task)
        .filter(
            Task.client_id == client_id,
            Task.deleted_at.is_(None),
            Task.status != "done",
            Task.due_date.isnot(None),
            Task.due_date < now,
        )
        .count()
    )

    project_ids = [
        p.id
        for p in db.query(Project.id)
        .filter(Project.client_id == client_id, Project.deleted_at.is_(None))
        .all()
    ]

    open_engagement_count = (
        db.query(Project)
        .filter(
            Project.client_id == client_id,
            Project.deleted_at.is_(None),
            Project.status.in_(["planning", "active"]),
        )
        .count()
    )

    contracts_expiring_soon = 0
    if project_ids:
        cutoff = (now + timedelta(days=CONTRACT_RENEWAL_WARNING_DAYS)).date()
        contracts_expiring_soon = (
            db.query(Contract)
            .filter(
                Contract.project_id.in_(project_ids),
                Contract.deleted_at.is_(None),
                Contract.status == "signed",
                Contract.expiry_date.isnot(None),
                Contract.expiry_date <= cutoff,
                Contract.expiry_date >= now.date(),
            )
            .count()
        )

    high_risk_engagement_count = (
        db.query(Project)
        .filter(
            Project.client_id == client_id,
            Project.deleted_at.is_(None),
            Project.status.in_(["planning", "active"]),
            Project.risk_level == "high",
        )
        .count()
    )

    reasons: list[str] = []
    computed = "green"

    if overdue_task_count >= 3 or high_risk_engagement_count > 0:
        computed = "red"
    elif overdue_task_count >= 1 or contracts_expiring_soon > 0:
        computed = "amber"

    if overdue_task_count:
        reasons.append(f"{overdue_task_count} overdue task(s)")
    if contracts_expiring_soon:
        reasons.append(f"{contracts_expiring_soon} contract(s) expiring within {CONTRACT_RENEWAL_WARNING_DAYS} days")
    if high_risk_engagement_count:
        reasons.append(f"{high_risk_engagement_count} high-risk engagement(s)")
    if not reasons:
        reasons.append("No overdue work, expiring contracts, or high-risk engagements")

    return {
        "client_id": client_id,
        "computed_health": computed,
        "overdue_task_count": overdue_task_count,
        "open_engagement_count": open_engagement_count,
        "contracts_expiring_soon": contracts_expiring_soon,
        "reasons": reasons,
    }
