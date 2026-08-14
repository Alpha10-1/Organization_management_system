from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MilestoneBase(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = "pending"


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None


class MilestoneOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    achieved_at: Optional[datetime] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
