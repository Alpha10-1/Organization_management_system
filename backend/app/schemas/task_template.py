from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskTemplateItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    relative_due_days: Optional[int] = None
    order_index: int = 0


class TaskTemplateItemCreate(TaskTemplateItemBase):
    pass


class TaskTemplateItemOut(TaskTemplateItemBase):
    id: int
    template_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskTemplateBase(BaseModel):
    name: str
    engagement_type: Optional[str] = None
    description: Optional[str] = None
    trigger_event: Optional[str] = None  # onboarding | offboarding | null (engagement)
    department_id: Optional[int] = None


class TaskTemplateCreate(TaskTemplateBase):
    items: list[TaskTemplateItemCreate] = []


class TaskTemplateUpdate(BaseModel):
    name: Optional[str] = None
    engagement_type: Optional[str] = None
    description: Optional[str] = None
    trigger_event: Optional[str] = None
    department_id: Optional[int] = None


class TaskTemplateOut(TaskTemplateBase):
    id: int
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    items: list[TaskTemplateItemOut] = []

    model_config = {"from_attributes": True}


class TaskTemplateApplyRequest(BaseModel):
    project_id: int
    # If set, item due dates anchor to this date instead of the project's
    # start_date (or today, if the project has neither).
    anchor_date: Optional[datetime] = None


class TaskTemplateApplyToUserRequest(BaseModel):
    """Applies an onboarding/offboarding checklist to a person instead of
    a project: items become tasks assigned to them with no project/client
    attached, due dates anchored to anchor_date (defaults to today)."""

    user_email: str
    anchor_date: Optional[datetime] = None
