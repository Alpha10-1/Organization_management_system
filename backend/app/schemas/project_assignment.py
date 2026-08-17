from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ProjectAssignmentCreate(BaseModel):
    # Exactly one of these must be set -- assigning a user staffs that
    # person; assigning a department staffs everyone in it.
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Optional[str] = None
    allocation_percent: Optional[int] = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def _exactly_one_target(self):
        if bool(self.user_id) == bool(self.department_id):
            raise ValueError("Provide exactly one of user_id or department_id")
        if self.allocation_percent is not None and not self.user_id:
            raise ValueError("allocation_percent only applies to individual (user_id) assignments")
        return self


class ProjectAssignmentUpdate(BaseModel):
    role: Optional[str] = None
    allocation_percent: Optional[int] = Field(default=None, ge=1, le=100)


class ProjectAssignmentOut(BaseModel):
    id: int
    project_id: int
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    user_name: Optional[str] = None
    department_name: Optional[str] = None
    role: Optional[str] = None
    allocation_percent: Optional[int] = None
    assigned_by_email: str
    assigned_by_name: str
    created_at: datetime

    model_config = {"from_attributes": True}
