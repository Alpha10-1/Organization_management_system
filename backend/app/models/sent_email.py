from app.core.time import utcnow

from sqlalchemy import Column, DateTime, Integer, String, Text
from app.db.session import Base


class SentEmail(Base):
    """Outbox record for every 'sent' email. By default the app never talks
    to a paid mail provider: emails are written here (and logged to the
    console) instead, so password reset / verification flows work with zero
    hosting cost. If SMTP_HOST is configured via env vars, real emails are
    additionally sent through it -- entirely optional."""

    __tablename__ = "sent_emails"

    id = Column(Integer, primary_key=True, index=True)
    to_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    kind = Column(String(50), nullable=False, default="generic")
    created_at = Column(DateTime, default=utcnow)
