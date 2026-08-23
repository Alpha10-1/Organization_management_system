from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base

PROPOSAL_STATUSES = ("draft", "sent", "accepted", "rejected", "expired")


class Proposal(Base):
    """A proposal/quote sent to a prospect. A prospect can have several
    over time (a revised scope, a follow-up after a rejection), so this is
    a one-to-many child of Prospect rather than fields on Prospect itself
    -- the same reasoning as Contract being separate from Project so a
    renegotiated deal doesn't overwrite the record of what was originally
    offered.
    """

    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    scope_summary = Column(Text, nullable=True)
    proposed_value = Column(Numeric(12, 2), nullable=True)

    status = Column(String(20), nullable=False, default="draft", index=True)

    sent_date = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    decided_at = Column(DateTime, nullable=True)
    decided_by_email = Column(String(255), nullable=True)
    decided_by_name = Column(String(255), nullable=True)
    decision_notes = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
