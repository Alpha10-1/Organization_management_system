from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class StaffSkillBase(BaseModel):
    user_id: int
    name: str
    category: str = "skill"  # skill | certification
    proficiency_level: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class StaffSkillCreate(StaffSkillBase):
    pass


class StaffSkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    proficiency_level: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class StaffSkillOut(BaseModel):
    id: int
    user_id: int
    name: str
    category: str
    proficiency_level: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StaffSkillMatrixEntry(BaseModel):
    user_id: int
    user_name: str
    department_id: Optional[int] = None
    skills: list[StaffSkillOut]
