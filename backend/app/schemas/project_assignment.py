from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class ProjectAssignmentCreate(BaseModel):
    # Exactly one of these must be set -- assigning a user staffs that
    # person; assigning a department staffs everyone in it.
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one_target(self):
        if bool(self.user_id) == bool(self.department_id):
            raise ValueError("Provide exactly one of user_id or department_id")
        return self


class ProjectAssignmentOut(BaseModel):
    id: int
    project_id: int
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    user_name: Optional[str] = None
    department_name: Optional[str] = None
    role: Optional[str] = None
    assigned_by_email: str
    assigned_by_name: str
    created_at: datetime

    model_config = {"from_attributes": True}
