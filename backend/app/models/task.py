from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)

    status = Column(String(20), nullable=False, default="open", index=True)  # open | in_progress | done
    priority = Column(String(20), nullable=False, default="medium")  # low | medium | high
    due_date = Column(DateTime, nullable=True, index=True)

    assigned_to_email = Column(String(255), nullable=True, index=True)
    assigned_to_name = Column(String(255), nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
