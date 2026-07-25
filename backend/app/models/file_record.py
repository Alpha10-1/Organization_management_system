from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.db.session import Base


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=False, default=0)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    uploaded_by_email = Column(String(255), nullable=False)
    uploaded_by_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Versioning: re-uploading a file for the same slot creates a new row
    # pointing back at the one it replaces, instead of overwriting it.
    version = Column(Integer, nullable=False, default=1)
    previous_version_id = Column(Integer, ForeignKey("file_records.id"), nullable=True)
    # Soft delete: the DB row and the file on disk are both kept so a
    # deletion can be recovered; only visibility is toggled off.
    deleted_at = Column(DateTime, nullable=True, index=True)