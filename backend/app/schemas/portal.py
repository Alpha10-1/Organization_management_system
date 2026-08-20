from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PortalEngagementOut(BaseModel):
    """A scoped-down view of a Project for the client portal -- omits
    internal-only fields (budget, billing_notes, close_out_notes,
    risk_level, compliance_flag, created_by) that clients have no
    business seeing."""

    id: int
    name: str
    type: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    description: Optional[str] = None
    engagement_partner_name: Optional[str] = None
    engagement_manager_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PortalFileOut(BaseModel):
    """A scoped-down view of a FileRecord for the client portal -- omits
    internal storage details (stored_name, file_path)."""

    id: int
    original_name: str
    file_type: Optional[str] = None
    file_size: int
    uploaded_by_name: str
    created_at: datetime
    version: int = 1

    model_config = {"from_attributes": True}
