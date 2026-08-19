from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IndependenceDisclosureCreate(BaseModel):
    # Omitted (or set to another user by an admin) to log a disclosure on
    # someone else's behalf -- e.g. compliance recording something raised
    # in an interview. Defaults to the caller when not provided.
    user_id: Optional[int] = None
    client_id: Optional[int] = None
    disclosure_type: str
    description: str


class IndependenceDisclosureUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None  # active | resolved


class IndependenceDisclosureOut(BaseModel):
    id: int
    user_id: int
    client_id: Optional[int] = None
    disclosure_type: str
    description: str
    status: str
    resolved_at: Optional[datetime] = None
    resolved_by_email: Optional[str] = None
    resolved_by_name: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConflictCheckOut(BaseModel):
    user_id: int
    client_id: int
    has_conflict: bool
    disclosures: list[IndependenceDisclosureOut]


class ConflictOverrideCreate(BaseModel):
    project_id: int
    user_id: int
    reason: str


class ConflictOverrideOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    client_id: int
    disclosure_ids: list[int]
    reason: str
    overridden_by_email: str
    overridden_by_name: str
    created_at: datetime

    model_config = {"from_attributes": True}
