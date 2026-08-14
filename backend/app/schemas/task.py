from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

VALID_RECURRENCE_RULES = {"daily", "weekly", "monthly"}


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assigned_to_email: Optional[EmailStr] = None
    recurrence_rule: Optional[str] = None
    recurrence_end_date: Optional[datetime] = None

    @field_validator("recurrence_rule")
    @classmethod
    def validate_recurrence_rule(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_RECURRENCE_RULES:
            raise ValueError(f"recurrence_rule must be one of: {sorted(VALID_RECURRENCE_RULES)}")
        return v


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to_email: Optional[EmailStr] = None
    status: Optional[str] = None
    recurrence_rule: Optional[str] = None
    recurrence_end_date: Optional[datetime] = None

    @field_validator("recurrence_rule")
    @classmethod
    def validate_recurrence_rule(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_RECURRENCE_RULES:
            raise ValueError(f"recurrence_rule must be one of: {sorted(VALID_RECURRENCE_RULES)}")
        return v


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    assigned_to_email: Optional[str] = None
    assigned_to_name: Optional[str] = None
    recurrence_rule: Optional[str] = None
    recurrence_end_date: Optional[datetime] = None
    recurrence_parent_id: Optional[int] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskDetail(TaskOut):
    """Task with rolled-up subtask/dependency info, used on the task detail
    view so the frontend doesn't need extra round-trips."""

    subtask_count: int = 0
    open_subtask_count: int = 0
    blocked_by: list[int] = []  # task IDs this task is waiting on
    blocks: list[int] = []  # task IDs waiting on this task
    is_blocked: bool = False  # true if any blocked_by task isn't done
