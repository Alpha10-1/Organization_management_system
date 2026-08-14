from app.core.time import utcnow

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.db.session import Base


class ClientContact(Base):
    """A single person at a client organization (CFO, controller,
    procurement, etc). Split out from the single Client record so a client
    can have many contacts, with one flagged as primary for default
    correspondence."""

    __tablename__ = "client_contacts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=True)  # e.g. CFO, Controller, Procurement
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
