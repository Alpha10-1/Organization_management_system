from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base


class Contract(Base):
    """A contract / engagement letter / SOW tied to a single engagement.
    Tracking contract value against hours logged (see time_entry.py) gives
    margin visibility even without full invoicing."""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    # fixed_fee | hourly | retainer
    billing_type = Column(String(20), nullable=False, default="fixed_fee", index=True)
    # Total contract value for fixed_fee/retainer; for hourly this is an
    # optional not-to-exceed cap.
    value = Column(Numeric(12, 2), nullable=True)
    # Only meaningful when billing_type == "hourly" (or as the effective
    # rate backing a retainer).
    hourly_rate = Column(Numeric(10, 2), nullable=True)

    signed_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)

    # draft | sent | signed | expired | terminated
    status = Column(String(20), nullable=False, default="draft", index=True)

    notes = Column(Text, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
