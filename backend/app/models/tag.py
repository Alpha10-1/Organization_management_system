from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from app.db.session import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(20), nullable=False, default="#6366f1")
    created_at = Column(DateTime, default=utcnow)


class ClientTag(Base):
    """Join table linking clients to tags (many-to-many)."""

    __tablename__ = "client_tags"
    __table_args__ = (UniqueConstraint("client_id", "tag_id", name="uq_client_tag"),)

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)
