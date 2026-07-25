from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.time import utcnow

from app.db.session import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="Active", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    # Soft delete: deleted clients are kept for audit/recovery purposes and
    # simply excluded from normal queries (see routes/clients.py).
    deleted_at = Column(DateTime, nullable=True, index=True)