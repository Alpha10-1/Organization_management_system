from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assigned_to_email: Optional[EmailStr] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to_email: Optional[EmailStr] = None
    status: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    assigned_to_email: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
