from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileRecordOut(BaseModel):
    id: int
    original_name: str
    stored_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: int
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    uploaded_by_email: str
    uploaded_by_name: str
    created_at: datetime
    version: int = 1
    previous_version_id: Optional[int] = None

    model_config = {"from_attributes": True}