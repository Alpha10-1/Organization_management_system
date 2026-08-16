from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    department_head_user_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_head_user_id: Optional[int] = None


class DepartmentOut(DepartmentBase):
    id: int
    department_head_user_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
