"""Rules-based anomaly detection over logged time entries.

This is a partner-review and audit-quality tool, not a fraud accusation
engine -- every flag is an explainable heuristic (not a black-box score)
because a partner needs to be able to look at a flagged entry and see
exactly why it was surfaced. Kept in the same on-demand-computation style
as budget.py/engagement_health.py: nothing is persisted, findings are
recomputed fresh from TimeEntry rows every time they're requested.
"""

from collections import defaultdict
from datetime import date as date_type, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.time_entry import TimeEntry

# An entry logged more than this many days after the work date is "stale" --
# long enough after the fact that recall (and therefore accuracy) is
# questionable, and a classic WIP-padding pattern (backfilling hours near a
# billing cutoff).
LATE_LOG_THRESHOLD_DAYS = 14

# A single Friday entry at/above this many hours is flagged for review --
# not inherently wrong, but a common pattern worth a second look (hours
# parked before the weekend rather than logged against the day they were
# actually worked).
FRIDAY_LARGE_HOURS_THRESHOLD = Decimal("6")

# Hours values common enough to be suspicious when they repeat exactly,
# rather than varying the way genuinely-tracked time usually does.
ROUND_HOURS_VALUES = {Decimal("4"), Decimal("4.00"), Decimal("8"), Decimal("8.00")}
ROUND_REPEAT_THRESHOLD = 3  # same user, same project, same exact hours, this many times+


def _as_aware(dt):
    from datetime import timezone

    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def detect_time_entry_anomalies(
    db: Session,
    project_id: int | None = None,
    user_email: str | None = None,
    since: date_type | None = None,
) -> list[dict]:
    """Returns one dict per flagged TimeEntry: {time_entry_id, project_id,
    user_email, user_name, entry_date, hours, flags, reasons}. Entries with
    no flags are omitted entirely."""

    query = db.query(TimeEntry).filter(TimeEntry.deleted_at.is_(None))
    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    if user_email is not None:
        query = query.filter(TimeEntry.user_email == user_email)
    if since is not None:
        query = query.filter(TimeEntry.entry_date >= since)

    entries = query.order_by(TimeEntry.entry_date.asc()).all()

    # Group by (user_email, project_id, hours) to find round-number repeats,
    # and by (user_email, project_id, entry_date, hours) to find duplicates.
    round_repeat_groups: dict[tuple, list[TimeEntry]] = defaultdict(list)
    duplicate_groups: dict[tuple, list[TimeEntry]] = defaultdict(list)

    for e in entries:
        duplicate_groups[(e.user_email, e.project_id, e.entry_date, e.hours)].append(e)
        if e.hours in ROUND_HOURS_VALUES:
            round_repeat_groups[(e.user_email, e.project_id, e.hours)].append(e)

    findings: dict[int, dict] = {}

    def _flag(entry: TimeEntry, flag: str, reason: str) -> None:
        record = findings.setdefault(
            entry.id,
            {
                "time_entry_id": entry.id,
                "project_id": entry.project_id,
                "user_email": entry.user_email,
                "user_name": entry.user_name,
                "entry_date": entry.entry_date,
                "hours": entry.hours,
                "flags": [],
                "reasons": [],
            },
        )
        if flag not in record["flags"]:
            record["flags"].append(flag)
            record["reasons"].append(reason)

    now = utcnow()
    for e in entries:
        created_at = _as_aware(e.created_at)

        # 1. Logged well after the work date.
        if created_at is not None:
            lag_days = (created_at.date() - e.entry_date).days
            if lag_days > LATE_LOG_THRESHOLD_DAYS:
                _flag(
                    e,
                    "late_logged",
                    f"Logged {lag_days} days after the work date (threshold {LATE_LOG_THRESHOLD_DAYS})",
                )

        # 2. Large Friday-afternoon-style block.
        if e.entry_date.weekday() == 4 and e.hours >= FRIDAY_LARGE_HOURS_THRESHOLD:
            _flag(
                e,
                "friday_large_block",
                f"{e.hours}h logged on a Friday (threshold {FRIDAY_LARGE_HOURS_THRESHOLD}h)",
            )

        # 3. Duplicate-looking entry: same user/project/date/hours more than once.
        dupes = duplicate_groups[(e.user_email, e.project_id, e.entry_date, e.hours)]
        if len(dupes) > 1:
            _flag(
                e,
                "possible_duplicate",
                f"{len(dupes)} entries with identical hours ({e.hours}h) on the same date for this project",
            )

        # 4. Round-number padding: same user/project logs the same round
        # hours value repeatedly.
        if e.hours in ROUND_HOURS_VALUES:
            repeats = round_repeat_groups[(e.user_email, e.project_id, e.hours)]
            if len(repeats) >= ROUND_REPEAT_THRESHOLD:
                _flag(
                    e,
                    "round_number_pattern",
                    f"{e.hours}h logged {len(repeats)} times on this project by the same user",
                )

    # Preserve chronological order in the returned list.
    return [findings[e.id] for e in entries if e.id in findings]
