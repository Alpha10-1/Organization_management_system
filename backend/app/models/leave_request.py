from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class LeaveRequest(Base):
    """A leave/PTO request routed to the requester's manager (User.manager_id)
    for approval, rather than to a department-wide inbox -- mirrors how the
    org chart already models who reports to whom."""

    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Resolved from User.manager_id at request time and stored, so the
    # approval chain doesn't silently change if the org chart is edited
    # after the request was submitted.
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # pto | sick | unpaid | other
    leave_type = Column(String(20), nullable=False, default="pto", index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)

    # pending | approved | rejected | cancelled
    status = Column(String(20), nullable=False, default="pending", index=True)

    decided_at = Column(DateTime, nullable=True)
    decided_by_email = Column(String(255), nullable=True)
    decided_by_name = Column(String(255), nullable=True)
    decision_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
