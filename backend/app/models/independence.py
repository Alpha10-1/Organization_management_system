from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class IndependenceDisclosure(Base):
    """A staff member's self-reported (or admin-logged) financial/personal
    interest that could compromise independence on a given client -- e.g. a
    stock holding, a family relationship, or prior employment. This is the
    PCAOB/SEC-style independence register: firms are required to check
    staff for these conflicts *before* staffing them on an engagement, not
    just document them after the fact.

    client_id is nullable: a disclosure can be firm-wide/general (e.g. "my
    spouse works in banking industry-wide") without pointing at a specific
    client in the system yet. Only disclosures with a client_id are used
    for automatic conflict checks (see app.core.independence) -- a null
    client_id disclosure is still visible on the register for manual
    compliance review, but deliberately isn't matched against every
    engagement, which would make it useless noise.
    """

    __tablename__ = "independence_disclosures"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)

    # financial_interest | family_relationship | prior_employment | other
    disclosure_type = Column(String(30), nullable=False, index=True)
    description = Column(Text, nullable=False)

    # active | resolved -- resolved means the situation has ended (e.g. the
    # stock was sold) but the record is kept for audit history rather than
    # deleted.
    status = Column(String(20), nullable=False, default="active", index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_email = Column(String(255), nullable=True)
    resolved_by_name = Column(String(255), nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)


class ConflictOverride(Base):
    """Audit record created when a partner/admin knowingly staffs someone
    onto an engagement despite an active independence conflict (e.g. the
    conflict is judged immaterial, or a safeguard like a second reviewer is
    put in place). Overriding is deliberately not silent -- every override
    is logged with who approved it, why, and exactly which disclosures were
    overridden, so it stands up to later PCAOB/SEC or internal QC review.
    """

    __tablename__ = "conflict_overrides"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Comma-separated IndependenceDisclosure ids that were active and
    # overridden at the time this record was created -- kept as a simple
    # delimited string (consistent with Comment.mentions elsewhere in this
    # codebase) rather than a join table, since it's write-once audit data.
    disclosure_ids = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)

    overridden_by_email = Column(String(255), nullable=False)
    overridden_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
