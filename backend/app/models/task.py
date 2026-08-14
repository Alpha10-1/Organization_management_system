from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Subtasks: a task with a parent_task_id is a checklist item under a
    # larger task rather than a top-level item.
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    status = Column(String(20), nullable=False, default="open", index=True)  # open | in_progress | done
    priority = Column(String(20), nullable=False, default="medium")  # low | medium | high
    due_date = Column(DateTime, nullable=True, index=True)

    # Recurrence: none | daily | weekly | monthly. When a recurring task is
    # marked done, the next occurrence is cloned automatically (see
    # routes/tasks.py) up to recurrence_end_date, if set.
    recurrence_rule = Column(String(20), nullable=True)
    recurrence_end_date = Column(DateTime, nullable=True)
    # Points from a generated occurrence back at the recurring task that
    # spawned it, so occurrences can be traced to their series.
    recurrence_parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    assigned_to_email = Column(String(255), nullable=True, index=True)
    assigned_to_name = Column(String(255), nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
