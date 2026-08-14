from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from app.db.session import Base


class TaskDependency(Base):
    """A directed 'is blocked by' edge between two tasks: `task_id` cannot
    be considered done until `depends_on_task_id` is done. Kept as its own
    table (rather than columns on Task) since a task can depend on more
    than one other task."""

    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency_pair"),)

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)

    created_at = Column(DateTime, default=utcnow)
