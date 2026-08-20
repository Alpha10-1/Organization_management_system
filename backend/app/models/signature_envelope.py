from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class SignatureEnvelope(Base):
    """A single e-signature request sent out for a Contract or
    ChangeOrder, and its resulting status. Polymorphic on
    (document_type, document_id) rather than two nullable FK columns --
    same convention already used by ActivityLog (entity_type/entity_id)
    for the same reason: one envelope table serves both document types
    without a join table per type, and a change order or contract can
    accumulate a history of envelopes (e.g. a voided-and-resent one)
    without a schema change when a third signable document type shows up
    later (e.g. Q2's own engagement-letter-as-first-contract already
    covers "contract"; this generalizes cleanly).
    """

    __tablename__ = "signature_envelopes"

    id = Column(Integer, primary_key=True, index=True)

    # "contract" | "change_order"
    document_type = Column(String(20), nullable=False, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    # Denormalized for per-engagement queries without a join, same as
    # ChangeOrder.project_id already denormalizes off Contract.
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # "mock" | "docusign" -- see app.core.esign
    provider = Column(String(20), nullable=False, default="mock")
    provider_envelope_id = Column(String(255), nullable=False, unique=True, index=True)

    signer_email = Column(String(255), nullable=False)
    signer_name = Column(String(255), nullable=False)

    # sent | completed | declined | voided
    status = Column(String(20), nullable=False, default="sent", index=True)

    sent_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    decline_reason = Column(Text, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    void_reason = Column(Text, nullable=True)

    requested_by_email = Column(String(255), nullable=False)
    requested_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
