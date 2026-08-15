from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base


class Project(Base):
    """An Engagement/Project: the unit of billable work a firm runs for a
    client. A client can have many concurrent engagements (an audit, a tax
    advisory project, a systems implementation), each with its own team,
    timeline and budget. Tasks, contracts and time entries all hang off a
    project rather than directly off the client."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    # audit | tax | advisory | systems_implementation | other (validated in routes)
    type = Column(String(50), nullable=False, default="other", index=True)
    # planning | active | on_hold | completed | cancelled
    status = Column(String(20), nullable=False, default="planning", index=True)

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Numeric(12, 2) comfortably covers engagement budgets in currency units
    # with cents, without floating-point rounding issues.
    budget = Column(Numeric(12, 2), nullable=True)

    engagement_partner_email = Column(String(255), nullable=True, index=True)
    engagement_partner_name = Column(String(255), nullable=True)
    engagement_manager_email = Column(String(255), nullable=True, index=True)
    engagement_manager_name = Column(String(255), nullable=True)

    description = Column(Text, nullable=True)

    # Optional extended detail, surfaced behind a "Specify More" toggle on
    # the create/edit form rather than cluttering the default view. None of
    # these are required to create a project.
    objectives = Column(Text, nullable=True)
    deliverables = Column(Text, nullable=True)
    stakeholders = Column(Text, nullable=True)
    billing_notes = Column(Text, nullable=True)

    # Risk & compliance tracking (feature 6) lives at the engagement level
    # since risk is usually assessed per-engagement, not per-client.
    risk_level = Column(String(20), nullable=False, default="low", index=True)  # low | medium | high
    compliance_flag = Column(String(50), nullable=True)  # free-text flag, e.g. "SOX", "PCAOB"

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
