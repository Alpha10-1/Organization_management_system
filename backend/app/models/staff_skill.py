from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class StaffSkill(Base):
    """A skill or certification held by a staff member, so engagement
    staffing decisions ('who can I put on this audit') are data-driven
    instead of tribal knowledge. Skills and certifications share one table
    -- a certification is just a skill entry with an expiry_date, rather
    than a second parallel model -- since both answer the same "can this
    person do X" question and are staffed the same way."""

    __tablename__ = "staff_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(150), nullable=False, index=True)
    # skill | certification
    category = Column(String(20), nullable=False, default="skill", index=True)
    # beginner | intermediate | advanced | expert -- most meaningful for
    # skills; certifications are more often held/not-held, so this stays
    # optional rather than forcing a proficiency rating onto a license.
    proficiency_level = Column(String(20), nullable=True)

    issued_date = Column(Date, nullable=True)
    # Certifications lapse; a null expiry_date means it doesn't (or isn't
    # tracked). Indexed so "certifications expiring soon" is a cheap scan.
    expiry_date = Column(Date, nullable=True, index=True)

    notes = Column(Text, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
