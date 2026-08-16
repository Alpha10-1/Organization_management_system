from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    # Nullable: not every department has a designated head, and the head
    # doesn't have to be scoped to this department at the DB level (kept
    # as a soft business rule enforced in the route instead).
    department_head_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow)
