from app.core.time import utcnow

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # task_assigned, file_uploaded, mention, role_changed, ...
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=utcnow, index=True)
