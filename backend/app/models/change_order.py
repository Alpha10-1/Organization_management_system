from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base


class ChangeOrder(Base):
    """A scope/fee change against a signed contract, tracked as its own
    line item rather than overwriting Contract.value and losing the
    history of why it changed. Denormalizes project_id from the contract
    (mirroring TimeEntry.project_id) so change orders can be queried
    per-engagement without an extra join."""

    __tablename__ = "change_orders"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # fee_increase | fee_decrease | scope_change | other
    change_type = Column(String(20), nullable=False, default="scope_change", index=True)

    # Delta applied to Contract.value when approved (positive or negative).
    amount_delta = Column(Numeric(12, 2), nullable=True)
    # Informational delta to estimated/contracted hours; not enforced
    # against a cap since Contract doesn't track estimated hours today.
    hours_delta = Column(Numeric(6, 2), nullable=True)

    # pending | approved | rejected
    status = Column(String(20), nullable=False, default="pending", index=True)
    requested_date = Column(Date, nullable=True)

    decided_at = Column(DateTime, nullable=True)
    decided_by_email = Column(String(255), nullable=True)
    decided_by_name = Column(String(255), nullable=True)

    # Set once a signature envelope for this change order (see
    # SignatureEnvelope) reaches a terminal state. Deliberately separate
    # from `status` (the internal approve/reject decision) -- a change
    # order can be internally approved (delta already applied to the
    # contract) while the client-facing signature is still outstanding,
    # same as a Contract can be "signed" internally before DocuSign's
    # copy comes back. sent | completed | declined | voided
    signature_status = Column(String(20), nullable=True, index=True)
    signed_at = Column(Date, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
