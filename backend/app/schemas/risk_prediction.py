from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel


class RiskForecastOut(BaseModel):
    """Forward-looking risk score for a single engagement: today's score
    plus a trend read from prior EngagementRiskSnapshot rows. health is the
    green/amber/red badge as it stands today; predicted_health is where the
    score says it's heading, which can be worse than current_health even
    while current_health is still green -- that gap is the whole point."""

    project_id: int
    risk_score: int
    current_health: str
    predicted_health: str
    signals: list[str]
    trend: str  # worsening | stable | improving | insufficient_data
    score_delta: Optional[int] = None
    baseline_date: Optional[date_type] = None
    baseline_score: Optional[int] = None
    lookback_days: int
    leading_indicator: bool


class AtRiskEngagement(BaseModel):
    project_id: int
    project_name: str
    client_id: int
    client_name: Optional[str] = None
    engagement_partner_name: Optional[str] = None
    risk_score: int
    current_health: str
    predicted_health: str
    trend: str
    score_delta: Optional[int] = None
    signals: list[str]
