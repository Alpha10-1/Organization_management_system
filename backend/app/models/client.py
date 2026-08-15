from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from app.core.time import utcnow

from app.db.session import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)

    # business | individual | npo. Most firm clients are organizations, so
    # "business" is the default; "individual" covers clients dealing with
    # a firm as a person (e.g. private tax clients), and "npo" covers
    # not-for-profit engagements which usually need the same organizational
    # detail as a business but are tracked separately for reporting.
    client_type = Column(String(20), nullable=False, default="business", index=True)

    # Individual clients (or the named contact for a business/NPO record).
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Organization detail -- required for business/npo, unused for individual.
    company_name = Column(String(255), nullable=True, index=True)
    registration_number = Column(String(100), nullable=True)
    tax_number = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True, index=True)
    website = Column(String(255), nullable=True)

    billing_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

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

    @property
    def display_name(self) -> str:
        """Human-readable label used across search, activity logs and
        exports. Business/NPO clients are known by their company name;
        individuals by their first/last name."""
        if self.client_type in ("business", "npo") and self.company_name:
            return self.company_name
        name = " ".join(part for part in [self.first_name, self.last_name] if part)
        return name or self.company_name or f"Client #{self.id}"