from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkpaperCreate(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    file_id: Optional[int] = None
    # Defaults to the caller when omitted -- set explicitly when an admin
    # or manager is logging a workpaper on a preparer's behalf.
    preparer_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    partner_id: Optional[int] = None


class WorkpaperUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    file_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    partner_id: Optional[int] = None


class WorkpaperReviewEventOut(BaseModel):
    id: int
    workpaper_id: int
    event_type: str
    notes: Optional[str] = None
    actor_email: str
    actor_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkpaperOut(BaseModel):
    id: int
    project_id: int
    file_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    stage: str

    preparer_id: int
    prepared_by_email: str
    prepared_by_name: str
    submitted_for_review_at: Optional[datetime] = None

    reviewer_id: Optional[int] = None
    review_status: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by_email: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None

    partner_id: Optional[int] = None
    partner_status: Optional[str] = None
    partner_signed_off_at: Optional[datetime] = None
    partner_by_email: Optional[str] = None
    partner_by_name: Optional[str] = None
    partner_notes: Optional[str] = None

    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkpaperSubmitRequest(BaseModel):
    # Allows assigning/changing the reviewer at submission time if it
    # wasn't set when the workpaper was created.
    reviewer_id: Optional[int] = None
    notes: Optional[str] = None


class WorkpaperReviewDecision(BaseModel):
    status: str  # approved | rejected
    notes: Optional[str] = None


class WorkpaperPartnerDecision(BaseModel):
    status: str  # approved | rejected
    notes: Optional[str] = None
