from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PBCRequestBase(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None


class PBCRequestCreate(PBCRequestBase):
    pass


class PBCRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None


class PBCRequestReview(BaseModel):
    status: str  # approved | rejected
    notes: Optional[str] = None


class PBCRequestOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    file_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    submitted_by_email: Optional[str] = None
    submitted_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by_email: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    requested_by_email: str
    requested_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
