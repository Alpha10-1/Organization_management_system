from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class ClientNote(Base):
    """A single dated note entry for a client. Unlike Client.notes (a single
    free-text field that gets overwritten on every edit), this keeps a full
    running history of who said what and when."""

    __tablename__ = "client_notes"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    author_email = Column(String(255), nullable=False)
    author_name = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
