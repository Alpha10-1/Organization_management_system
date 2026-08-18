from sqlalchemy.orm import relationship

from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class TaskTemplate(Base):
    """A reusable checklist for a given engagement type (e.g. a standard
    'Audit Kickoff' checklist), cloned onto a project via
    routes/task_templates.py's /apply endpoint rather than re-created by
    hand on every new engagement."""

    __tablename__ = "task_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # audit | tax | advisory | systems_implementation | other | null (generic)
    engagement_type = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)

    # Onboarding/offboarding checklists reuse this same template pattern
    # rather than a separate model -- a template with trigger_event set is
    # applied to a person joining/leaving a department instead of to a
    # project. department_id scopes it to one department's checklist (e.g.
    # Tax's onboarding differs from Advisory's); null means firm-wide.
    trigger_event = Column(String(20), nullable=True, index=True)  # onboarding | offboarding | null (engagement)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)

    items = relationship(
        "TaskTemplateItem",
        order_by="TaskTemplateItem.order_index",
        cascade="all, delete-orphan",
    )


class TaskTemplateItem(Base):
    """A single checklist line on a TaskTemplate. relative_due_days is an
    offset (in days) applied against the target project's start_date -- or
    today, if the project has no start_date -- when the template is
    applied."""

    __tablename__ = "task_template_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False, default="medium")
    relative_due_days = Column(Integer, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=utcnow)
