from app.core.time import utcnow

from sqlalchemy import Column, DateTime, Integer, String, Text
from app.db.session import Base


class Comment(Base):
    """A generic comment attached to any entity (activity_log, client, task,
    file). entity_type + entity_id is a lightweight polymorphic reference,
    consistent with how ActivityLog already references entities."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    author_email = Column(String(255), nullable=False)
    author_name = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    mentions = Column(Text, nullable=True)  # comma-separated emails mentioned via @
    created_at = Column(DateTime, default=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
