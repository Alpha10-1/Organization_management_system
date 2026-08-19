"""Billing math shared between the invoices routes and reports: resolving
what a given hour of work is worth, and rolling that up into WIP and
realization-rate figures.

Rate resolution order for a project:
  1. The project's active signed contract's hourly_rate, if it has one
     (covers billing_type == "hourly", and any contract that records an
     effective rate for a retainer).
  2. Otherwise, fall back per-entry to the logging user's
     User.standard_billing_rate.
  3. If neither is set, the entry has no resolvable rate -- it still
     counts toward WIP hours, but is excluded from WIP/realization dollar
     figures (rather than silently valuing it at 0, which would distort
     realization rates downward).
"""

from dataclasses import dataclass, field
from datetime import date as date_type
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.time_entry import TimeEntry
from app.models.user import User

TWO_PLACES = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Round a monetary Decimal to 2 places, half-up, so amounts computed
    from hours*rate multiplication (which can produce more than 2 decimal
    places) always serialize the way every other currency field in this
    app does."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def project_hourly_rate(db: Session, project_id: int) -> Decimal | None:
    """The contract-level rate to use for this project, if any. Prefers the
    most recently signed contract with a status of 'signed' and a set
    hourly_rate; falls back to any contract with an hourly_rate if none are
    signed yet, so WIP still has a rate to work with during drafting."""
    contract = (
        db.query(Contract)
        .filter(
            Contract.project_id == project_id,
            Contract.deleted_at.is_(None),
            Contract.hourly_rate.isnot(None),
        )
        .order_by((Contract.status == "signed").desc(), Contract.signed_date.desc().nullslast())
        .first()
    )
    return contract.hourly_rate if contract else None


def resolve_rate(db: Session, entry: TimeEntry, *, project_rate_cache: dict[int, Decimal | None] | None = None) -> Decimal | None:
    """The rate ($/hr) that applies to a single time entry, per the
    resolution order documented above."""
    cache = project_rate_cache if project_rate_cache is not None else {}
    if entry.project_id not in cache:
        cache[entry.project_id] = project_hourly_rate(db, entry.project_id)
    rate = cache[entry.project_id]
    if rate is not None:
        return rate

    user = db.query(User).filter(User.email == entry.user_email).first()
    if user and user.standard_billing_rate is not None:
        return user.standard_billing_rate
    return None


@dataclass
class WipSummary:
    project_id: int
    total_hours: Decimal = Decimal("0.00")
    valued_hours: Decimal = Decimal("0.00")
    unrated_hours: Decimal = Decimal("0.00")
    wip_value: Decimal = Decimal("0.00")
    entry_count: int = 0
    entries: list[TimeEntry] = field(default_factory=list)


def compute_wip(db: Session, project_id: int) -> WipSummary:
    """WIP = billable time entries logged against this project that
    haven't been pulled onto an invoice yet. This is literally "work
    happened, money not yet captured" -- the core gap billing closes."""
    entries = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.project_id == project_id,
            TimeEntry.deleted_at.is_(None),
            TimeEntry.billable.is_(True),
            TimeEntry.invoice_line_item_id.is_(None),
        )
        .order_by(TimeEntry.entry_date.asc())
        .all()
    )

    summary = WipSummary(project_id=project_id)
    rate_cache: dict[int, Decimal | None] = {}
    for entry in entries:
        summary.total_hours += entry.hours
        summary.entry_count += 1
        summary.entries.append(entry)
        rate = resolve_rate(db, entry, project_rate_cache=rate_cache)
        if rate is not None:
            summary.valued_hours += entry.hours
            summary.wip_value += money(entry.hours * rate)
        else:
            summary.unrated_hours += entry.hours

    return summary


@dataclass
class RealizationRow:
    key: str
    label: str
    worked_value: Decimal = Decimal("0.00")
    billed_value: Decimal = Decimal("0.00")
    worked_hours: Decimal = Decimal("0.00")

    @property
    def realization_rate(self) -> Decimal | None:
        if self.worked_value == 0:
            return None
        return (self.billed_value / self.worked_value).quantize(Decimal("0.0001"))


def compute_realization(
    db: Session,
    *,
    group_by: str,
    start_date: date_type | None,
    end_date: date_type | None,
    project_id: int | None = None,
    department_by_project: dict[int, tuple[int, str] | None] | None = None,
) -> list[RealizationRow]:
    """Realization rate = billed value / worked value, grouped by
    engagement (project), partner (engagement_partner_email), or
    department. 'Worked value' is time-entry hours valued via
    resolve_rate over the period; 'billed value' is the amount actually
    invoiced (excluding void invoices) for line items tied to time entries
    logged in that same period -- so a rate always compares like to like
    (work done in the window vs. what that specific work billed for, not
    whatever happened to be invoiced in the window).
    """
    from app.models.project import Project  # local import: avoids a cycle with department_scope

    query = db.query(TimeEntry).filter(TimeEntry.deleted_at.is_(None), TimeEntry.billable.is_(True))
    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    if start_date is not None:
        query = query.filter(TimeEntry.entry_date >= start_date)
    if end_date is not None:
        query = query.filter(TimeEntry.entry_date <= end_date)
    entries = query.all()

    if not entries:
        return []

    project_ids = {e.project_id for e in entries}
    projects = {p.id: p for p in db.query(Project).filter(Project.id.in_(project_ids)).all()}

    # Preload billed amounts for line items tied to these entries in one query.
    entry_ids = [e.id for e in entries]
    billed_by_entry: dict[int, Decimal] = {}
    if entry_ids:
        rows = (
            db.query(InvoiceLineItem.id, InvoiceLineItem.amount, TimeEntry.id)
            .join(TimeEntry, TimeEntry.invoice_line_item_id == InvoiceLineItem.id)
            .join(Invoice, Invoice.id == InvoiceLineItem.invoice_id)
            .filter(TimeEntry.id.in_(entry_ids), Invoice.status != "void", Invoice.deleted_at.is_(None))
            .all()
        )
        for _line_item_id, amount, time_entry_id in rows:
            billed_by_entry[time_entry_id] = (billed_by_entry.get(time_entry_id) or Decimal("0")) + (amount or Decimal("0"))

    rate_cache: dict[int, Decimal | None] = {}
    rows_by_key: dict[str, RealizationRow] = {}

    for entry in entries:
        project = projects.get(entry.project_id)
        if project is None:
            continue

        if group_by == "project":
            key, label = str(project.id), project.name
        elif group_by == "partner":
            key = project.engagement_partner_email or "unassigned"
            label = project.engagement_partner_name or "Unassigned"
        elif group_by == "department":
            dept = (department_by_project or {}).get(project.id)
            key = str(dept[0]) if dept else "unassigned"
            label = dept[1] if dept else "Unassigned"
        else:
            key, label = str(project.id), project.name

        row = rows_by_key.setdefault(key, RealizationRow(key=key, label=label))
        row.worked_hours += entry.hours

        rate = resolve_rate(db, entry, project_rate_cache=rate_cache)
        if rate is not None:
            row.worked_value += money(entry.hours * rate)

        if entry.id in billed_by_entry:
            row.billed_value += billed_by_entry[entry.id]

    return sorted(rows_by_key.values(), key=lambda r: r.label.lower())
