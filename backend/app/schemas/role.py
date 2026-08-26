from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: list[str]
    is_system: bool
    created_by_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCustomRoleUpdate(BaseModel):
    custom_role_id: Optional[int] = None
