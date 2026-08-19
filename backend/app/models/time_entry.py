from app.core.time import utcnow

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base


class TimeEntry(Base):
    """A single logged block of work against an engagement, optionally
    against a specific task within it. This is the raw feed for utilization
    rates, project profitability, and (eventually) billing -- so every
    entry is anchored to a project, not just a client or task."""

    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    user_email = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255), nullable=False)

    # Numeric rather than float: hours feed budget/margin math where
    # repeated float rounding would drift over hundreds of entries.
    hours = Column(Numeric(5, 2), nullable=False)
    entry_date = Column(Date, nullable=False, index=True)
    billable = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(Text, nullable=True)

    # Set once this entry has been pulled onto an invoice (see
    # InvoiceLineItem). Null + billable=True is exactly the definition of
    # "in WIP" -- worked, billable, not yet billed. Voiding or deleting the
    # invoice clears this back to null so the hours return to WIP.
    invoice_line_item_id = Column(
        Integer, ForeignKey("invoice_line_items.id"), nullable=True, index=True
    )

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
