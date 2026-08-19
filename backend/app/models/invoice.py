from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base


class Invoice(Base):
    """A bill sent to a client for work done on an engagement. Generated
    from WIP (uninvoiced billable time entries -- see TimeEntry) plus any
    manual/fixed-fee line items, an invoice is the missing link between
    time tracked and revenue actually captured: Project.budget and
    Contract.value tell you what work was scoped, TimeEntry tells you what
    was worked, and Invoice tells you what was billed. Realization rate
    (billed vs. worked) is derived by comparing invoice totals against the
    value of time entries over the same period -- see app.core.billing.
    """

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)

    # Human-facing identifier, assigned once at creation (INV-{year}-{id}).
    # Kept as a separate column (rather than derived at read time) so it
    # never changes even if numbering conventions change later.
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)

    # draft | sent | paid | void
    # (an invoice past due_date with status="sent" is "overdue" -- derived
    # at read time from due_date rather than stored, so it can't go stale)
    status = Column(String(20), nullable=False, default="draft", index=True)

    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)

    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    amount_paid = Column(Numeric(12, 2), nullable=False, default=0)
    paid_date = Column(Date, nullable=True)

    notes = Column(Text, nullable=True)
    void_reason = Column(Text, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)


class InvoiceLineItem(Base):
    """A single billed line on an invoice. Either tied to a specific
    TimeEntry (a time-based line, the normal case) or a manual line with no
    time_entry_id (a fixed-fee milestone billing, a flat adjustment, an
    expense reimbursement, etc.). rate/hours/amount are snapshotted at
    invoice-generation time so a later change to a user's standard rate or
    a contract's hourly_rate never rewrites the amount on an
    already-issued invoice.
    """

    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)

    description = Column(String(500), nullable=False)
    hours = Column(Numeric(6, 2), nullable=True)
    rate = Column(Numeric(10, 2), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)

    created_at = Column(DateTime, default=utcnow)
