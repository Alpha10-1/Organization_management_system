from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class ResourceRequest(Base):
    """A request from one department to borrow staff from another for a
    single engagement -- e.g. Tax needs an Advisory specialist for one
    audit -- without permanently moving them (their department_id doesn't
    change). Approving creates a normal ProjectAssignment on the target
    engagement, so the loan shows up everywhere assignments already do."""

    __tablename__ = "resource_requests"

    id = Column(Integer, primary_key=True, index=True)
    requesting_department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    providing_department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # A specific person can be named, or the request can be left open
    # (role_needed only) for the providing department's head to fill.
    requested_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role_needed = Column(String(100), nullable=True)
    allocation_percent = Column(Integer, nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    # pending | approved | rejected | cancelled
    status = Column(String(20), nullable=False, default="pending", index=True)

    decided_at = Column(DateTime, nullable=True)
    decided_by_email = Column(String(255), nullable=True)
    decided_by_name = Column(String(255), nullable=True)

    requested_by_email = Column(String(255), nullable=False)
    requested_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
