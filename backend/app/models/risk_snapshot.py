from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class EngagementRiskSnapshot(Base):
    """A dated point-in-time capture of an engagement's predicted risk
    score. engagement_health.py answers "how does this engagement look
    right now"; this table is what lets risk_prediction.py answer "is it
    getting worse" -- a single computation has no history to compare
    against, so each risk-forecast call upserts one row per project per
    day and trend is read back from the last N of these.

    One row per (project_id, snapshot_date): recomputing risk on a day
    that's already been snapshotted just updates that row in place rather
    than piling up duplicates."""

    __tablename__ = "engagement_risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)

    risk_score = Column(Integer, nullable=False)  # 0-100, higher = worse
    current_health = Column(String(10), nullable=False)  # green | amber | red (today's actual)
    predicted_health = Column(String(10), nullable=False)  # green | amber | red (forecast)
    overdue_task_count = Column(Integer, nullable=False, default=0)
    percent_budget_consumed = Column(Integer, nullable=True)

    # JSON-encoded list of human-readable contributing signals, stored as
    # text rather than a JSON column type to match the rest of the models
    # in this codebase (no JSON columns used elsewhere).
    signals = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
