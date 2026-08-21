from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class DocumentExtraction(Base):
    """The result of running document intelligence over a single uploaded
    FileRecord: figures, dates, and labeled line items pulled out so the
    engagement doesn't have to be hand-populated from a PDF/trial balance
    the client already sent. One row per file, re-run in place (an
    extraction is a derived view of the file, not an independent fact) --
    so re-extracting updates the existing row instead of appending.

    Kept as its own table (rather than columns on FileRecord) since most
    files never go through extraction and the payload is bulky."""

    __tablename__ = "document_extractions"

    id = Column(Integer, primary_key=True, index=True)
    file_record_id = Column(Integer, ForeignKey("file_records.id"), nullable=False, unique=True, index=True)

    # success | unsupported_type | empty | error
    status = Column(String(20), nullable=False, default="success", index=True)

    # JSON-encoded lists/dicts stored as text, matching the rest of this
    # codebase's convention of not using a JSON column type.
    amounts = Column(Text, nullable=True)  # [{"label": "Total Revenue", "value": "1,234,567", "context": "..."}]
    dates = Column(Text, nullable=True)  # ["2026-03-31", ...]
    labeled_figures = Column(Text, nullable=True)  # {"total_revenue": "1,234,567", "net_income": "..."}

    excerpt = Column(Text, nullable=True)  # short preview of the text that was scanned, for sanity-checking

    extracted_by_email = Column(String(255), nullable=False)
    extracted_by_name = Column(String(255), nullable=False)
    extracted_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
