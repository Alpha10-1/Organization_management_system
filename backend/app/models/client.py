from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
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
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

    # Group structures: a subsidiary points back at its parent so client
    # hierarchies (e.g. a holding company and its operating entities) can be
    # rolled up in reporting without duplicating client records.
    parent_client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)

    # Manual override for the relationship-health indicator surfaced on
    # partner dashboards (green|amber|red). When null, it's computed from
    # overdue tasks / contract renewal proximity instead -- see
    # app.core.client_health.
    relationship_health = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    # Soft delete: deleted clients are kept for audit/recovery purposes and
    # simply excluded from normal queries (see routes/clients.py).
    deleted_at = Column(DateTime, nullable=True, index=True)