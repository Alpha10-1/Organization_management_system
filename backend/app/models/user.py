from app.core.time import utcnow

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String

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

    # Standard hourly billing rate used to value WIP (work-in-progress) and
    # compute realization rates when the engagement's contract doesn't
    # itself carry an hourly rate (e.g. a fixed_fee contract still needs a
    # "value of hours worked" figure to measure billed-vs-worked against).
    # A contract-level hourly_rate, when present, always takes precedence
    # over this for rate resolution -- see app.core.billing.
    standard_billing_rate = Column(Numeric(10, 2), nullable=True)

    # Baseline hours/week this person is expected to be available for
    # billable + internal work. Used purely for capacity forecasting (see
    # app.core.capacity_forecast) to turn assignment allocation_percent
    # figures into actual hour counts and over/under-booking signals.
    # Defaults to a standard full-time week; overridable for part-time
    # staff.
    standard_weekly_hours = Column(Numeric(5, 2), nullable=False, default=40)

    # Email verification
    is_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String(255), nullable=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)

    # Password reset
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
