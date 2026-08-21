from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class TimeEntryAnomalyOut(BaseModel):
    time_entry_id: int
    project_id: int
    user_email: str
    user_name: str
    entry_date: date_type
    hours: Decimal
    flags: list[str]
    reasons: list[str]
