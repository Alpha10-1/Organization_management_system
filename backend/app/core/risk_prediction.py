"""Forward-looking risk scoring for an engagement.

engagement_health.py answers "how does this engagement look today" as a
green/amber/red snapshot. This module goes one step further: it turns the
same underlying signals (budget burn, overdue work, timeline) into a 0-100
score, tracks that score over time via EngagementRiskSnapshot, and reports
a trend -- so a partner can see an engagement sliding toward trouble while
it's still showing green, rather than finding out once it's already red.

The score is a transparent weighted heuristic, not a trained model: every
point added is traceable to a named signal (see `signals` in the return
value), which matters for a compliance-adjacent tool where a partner needs
to be able to explain *why* something was flagged.
"""

import json
from datetime import date as date_type, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.budget import compute_budget_burn
from app.core.engagement_health import compute_engagement_health
from app.core.time import utcnow
from app.models.project import Project
from app.models.risk_snapshot import EngagementRiskSnapshot

RISK_LEVEL_POINTS = {"low": 0, "medium": 15, "high": 30}
OVERDUE_TASK_POINTS_PER_TASK = 10
OVERDUE_TASK_POINTS_CAP = 30
MISSED_MILESTONE_POINTS_PER = 10
MISSED_MILESTONE_POINTS_CAP = 20
TIMELINE_SLIPPED_POINTS = 25
BUDGET_STATUS_POINTS = {"on_track": 0, "hours_only": 0, "no_budget": 0, "at_risk": 10, "over_budget": 25}

# If the engagement is burning budget faster than time is elapsing, that's
# a leading indicator independent of whether it's crossed the 80% alert
# threshold yet. Capped so a brand-new engagement with one large entry
# doesn't spike the score off a single data point.
BURN_VELOCITY_POINTS_CAP = 15

TREND_LOOKBACK_DAYS_DEFAULT = 14

# Chosen so that every individual signal which alone makes
# compute_engagement_health return "red" (risk_level high, 3+ overdue
# tasks, over-budget, timeline slipped) also alone crosses RED_THRESHOLD,
# and every individual signal which alone makes it return "amber" (risk
# medium, 1+ overdue task, at-risk budget, 1+ missed milestone) alone
# lands in the amber band. Combinations of several amber-level signals can
# then cross into predicted "red" territory before any single hard trigger
# does -- that gap is exactly the leading indicator this module exists for.
RED_THRESHOLD = 25
AMBER_THRESHOLD = 10


def _as_aware(dt: datetime) -> datetime:
    """SQLite round-trips datetimes as naive even when an aware value was
    stored, so any Python-level arithmetic (as opposed to a SQL filter,
    which SQLite compares fine) needs to normalize first -- otherwise this
    raises TypeError the first time it runs against a real ORM-loaded
    row. Naive values are assumed UTC, matching utcnow()'s Column default."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _elapsed_timeline_percent(project: Project) -> float | None:
    if project.start_date is None or project.end_date is None:
        return None
    start = _as_aware(project.start_date)
    end = _as_aware(project.end_date)
    total_days = (end - start).days
    if total_days <= 0:
        return None
    elapsed_days = (utcnow() - start).days
    return max(0.0, min(elapsed_days / total_days * 100, 200.0))


def _predicted_health(score: int) -> str:
    if score >= RED_THRESHOLD:
        return "red"
    if score >= AMBER_THRESHOLD:
        return "amber"
    return "green"


def compute_risk_score(db: Session, project: Project) -> dict:
    """Computes the current risk score and its component signals. Does not
    read or write any snapshot -- pure function of the engagement's current
    state, same pattern as compute_engagement_health / compute_budget_burn."""

    health = compute_engagement_health(db, project)
    burn = compute_budget_burn(db, project)

    score = 0
    signals: list[str] = []

    risk_points = RISK_LEVEL_POINTS.get(project.risk_level, 0)
    if risk_points:
        score += risk_points
        signals.append(f"Risk level '{project.risk_level}' contributes {risk_points} pts")

    overdue_points = min(health["overdue_task_count"] * OVERDUE_TASK_POINTS_PER_TASK, OVERDUE_TASK_POINTS_CAP)
    if overdue_points:
        score += overdue_points
        signals.append(f"{health['overdue_task_count']} overdue task(s) contribute {overdue_points} pts")

    milestone_points = min(
        health["missed_milestone_count"] * MISSED_MILESTONE_POINTS_PER, MISSED_MILESTONE_POINTS_CAP
    )
    if milestone_points:
        score += milestone_points
        signals.append(f"{health['missed_milestone_count']} missed milestone(s) contribute {milestone_points} pts")

    if health["timeline_slipped"]:
        score += TIMELINE_SLIPPED_POINTS
        signals.append(f"Timeline has slipped ({TIMELINE_SLIPPED_POINTS} pts)")

    budget_points = BUDGET_STATUS_POINTS.get(burn["status"], 0)
    if budget_points:
        score += budget_points
        signals.append(f"Budget status '{burn['status']}' contributes {budget_points} pts")

    elapsed_pct = _elapsed_timeline_percent(project)
    percent_consumed = burn["percent_consumed"]
    burn_velocity = None
    if elapsed_pct is not None and elapsed_pct > 0 and percent_consumed is not None:
        burn_velocity = percent_consumed / elapsed_pct
        if burn_velocity > 1.15:
            velocity_points = min(round((burn_velocity - 1) * 40), BURN_VELOCITY_POINTS_CAP)
            if velocity_points > 0:
                score += velocity_points
                signals.append(
                    f"Budget is being consumed {burn_velocity:.1f}x faster than the timeline is elapsing "
                    f"({velocity_points} pts)"
                )

    score = max(0, min(score, 100))

    if not signals:
        signals.append("No elevated risk signals detected")

    return {
        "project_id": project.id,
        "risk_score": score,
        "current_health": health["health"],
        "predicted_health": _predicted_health(score),
        "overdue_task_count": health["overdue_task_count"],
        "percent_budget_consumed": percent_consumed,
        "burn_velocity": burn_velocity,
        "signals": signals,
    }


def record_snapshot(db: Session, project: Project, on: date_type | None = None) -> EngagementRiskSnapshot:
    """Computes today's risk score and upserts the snapshot row for
    `on` (defaults to today). Idempotent per (project_id, date) -- calling
    this repeatedly in one day just refreshes the existing row."""

    snapshot_date = on or utcnow().date()
    result = compute_risk_score(db, project)

    existing = (
        db.query(EngagementRiskSnapshot)
        .filter(
            EngagementRiskSnapshot.project_id == project.id,
            EngagementRiskSnapshot.snapshot_date == snapshot_date,
        )
        .first()
    )

    percent_consumed = result["percent_budget_consumed"]
    percent_consumed_int = int(percent_consumed) if percent_consumed is not None else None

    if existing:
        existing.risk_score = result["risk_score"]
        existing.current_health = result["current_health"]
        existing.predicted_health = result["predicted_health"]
        existing.overdue_task_count = result["overdue_task_count"]
        existing.percent_budget_consumed = percent_consumed_int
        existing.signals = json.dumps(result["signals"])
        db.commit()
        db.refresh(existing)
        return existing

    snapshot = EngagementRiskSnapshot(
        project_id=project.id,
        snapshot_date=snapshot_date,
        risk_score=result["risk_score"],
        current_health=result["current_health"],
        predicted_health=result["predicted_health"],
        overdue_task_count=result["overdue_task_count"],
        percent_budget_consumed=percent_consumed_int,
        signals=json.dumps(result["signals"]),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_risk_forecast(db: Session, project: Project, lookback_days: int = TREND_LOOKBACK_DAYS_DEFAULT) -> dict:
    """Records today's snapshot, then compares it against the most recent
    prior snapshot at least `lookback_days` old to report a trend. If no
    older snapshot exists yet (new engagement, or forecasting just turned
    on), trend is "insufficient_data" rather than guessing."""

    today_snapshot = record_snapshot(db, project)
    result = compute_risk_score(db, project)

    cutoff = today_snapshot.snapshot_date - timedelta(days=lookback_days)
    baseline = (
        db.query(EngagementRiskSnapshot)
        .filter(
            EngagementRiskSnapshot.project_id == project.id,
            EngagementRiskSnapshot.snapshot_date <= cutoff,
        )
        .order_by(EngagementRiskSnapshot.snapshot_date.desc())
        .first()
    )

    if baseline is None:
        trend = "insufficient_data"
        score_delta = None
        baseline_date = None
        baseline_score = None
    else:
        score_delta = today_snapshot.risk_score - baseline.risk_score
        baseline_date = baseline.snapshot_date
        baseline_score = baseline.risk_score
        if score_delta >= 10:
            trend = "worsening"
        elif score_delta <= -10:
            trend = "improving"
        else:
            trend = "stable"

    # A "trending toward trouble" flag independent of trend direction: the
    # forecast is already worse than what's showing today, meaning the
    # green/amber health badge hasn't caught up to where the numbers are
    # heading yet. This is the leading-indicator case the roadmap calls out.
    health_rank = {"green": 0, "amber": 1, "red": 2}
    leading_indicator = health_rank[result["predicted_health"]] > health_rank[result["current_health"]]

    return {
        "project_id": project.id,
        "risk_score": result["risk_score"],
        "current_health": result["current_health"],
        "predicted_health": result["predicted_health"],
        "signals": result["signals"],
        "trend": trend,
        "score_delta": score_delta,
        "baseline_date": baseline_date,
        "baseline_score": baseline_score,
        "lookback_days": lookback_days,
        "leading_indicator": leading_indicator,
    }
