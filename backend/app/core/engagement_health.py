"""Computes a green/amber/red health signal for an engagement by rolling up
overdue tasks, budget burn, risk level, and timeline slippage -- the same
pattern as client relationship_health, but scoped per engagement for a
partner-level view. Kept separate from routes so it can be reused by both
the project health endpoint and the compliance/partner dashboards."""

from sqlalchemy.orm import Session

from app.core.budget import compute_budget_burn
from app.core.time import utcnow
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.task import Task

VALID_HEALTH_VALUES = {"green", "amber", "red"}


def compute_engagement_health(db: Session, project: Project) -> dict:
    now = utcnow()

    overdue_task_count = (
        db.query(Task)
        .filter(
            Task.project_id == project.id,
            Task.deleted_at.is_(None),
            Task.status != "done",
            Task.due_date.isnot(None),
            Task.due_date < now,
        )
        .count()
    )

    missed_milestone_count = (
        db.query(Milestone)
        .filter(
            Milestone.project_id == project.id,
            Milestone.deleted_at.is_(None),
            Milestone.status != "achieved",
            Milestone.due_date.isnot(None),
            Milestone.due_date < now,
        )
        .count()
    )

    timeline_slipped = bool(
        db.query(Project)
        .filter(
            Project.id == project.id,
            Project.end_date.isnot(None),
            Project.end_date < now,
            Project.status.in_(("planning", "active", "on_hold")),
        )
        .first()
    )

    burn = compute_budget_burn(db, project)
    budget_status = burn["status"]

    reasons: list[str] = []
    health = "green"

    if (
        project.risk_level == "high"
        or overdue_task_count >= 3
        or budget_status == "over_budget"
        or timeline_slipped
    ):
        health = "red"
    elif (
        project.risk_level == "medium"
        or overdue_task_count >= 1
        or budget_status == "at_risk"
        or missed_milestone_count >= 1
    ):
        health = "amber"

    if project.risk_level in ("high", "medium"):
        reasons.append(f"Risk level is {project.risk_level}")
    if overdue_task_count:
        reasons.append(f"{overdue_task_count} overdue task(s)")
    if missed_milestone_count:
        reasons.append(f"{missed_milestone_count} missed milestone(s)")
    if budget_status in ("at_risk", "over_budget"):
        reasons.append(f"Budget burn is {budget_status.replace('_', ' ')}")
    if timeline_slipped:
        reasons.append("End date has passed while engagement is still open")
    if not reasons:
        reasons.append("No overdue work, budget concerns, or timeline slippage")

    return {
        "project_id": project.id,
        "health": health,
        "reasons": reasons,
        "overdue_task_count": overdue_task_count,
        "missed_milestone_count": missed_milestone_count,
        "risk_level": project.risk_level,
        "budget_status": budget_status,
        "percent_budget_consumed": burn["percent_consumed"],
        "timeline_slipped": timeline_slipped,
    }
