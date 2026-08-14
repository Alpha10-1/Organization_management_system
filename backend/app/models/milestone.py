from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class Milestone(Base):
    """A project-level checkpoint (e.g. 'Fieldwork complete', 'Draft report
    issued'), distinct from individual tasks. Milestones anchor Gantt-style
    timelines and give partners a coarser progress signal than the full
    task list."""

    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True, index=True)

    # pending | achieved | missed
    status = Column(String(20), nullable=False, default="pending", index=True)
    achieved_at = Column(DateTime, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
