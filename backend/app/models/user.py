from app.core.time import utcnow

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.db.session import Base

# Ordered from most junior to most senior. Order matters -- it's used to
# rank staff for seniority-aware views (e.g. "who outranks whom" on an
# org chart) without a separate numeric column to keep in sync.
POSITION_LEVELS = [
    "associate",
    "senior_associate",
    "manager",
    "senior_manager",
    "director",
    "partner",
]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False, default="staff")
    disabled = Column(Boolean, nullable=False, default=False)
    hashed_password = Column(String(255), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

    # Staffing: seniority/title within the firm, and who they report to.
    # Deliberately separate from `role` (admin/staff), which controls
    # system permissions, not organizational seniority.
    position = Column(String(30), nullable=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Email verification
    is_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String(255), nullable=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)

    # Password reset
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
