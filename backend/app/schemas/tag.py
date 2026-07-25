from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TagBase(BaseModel):
    name: str
    color: str = "#6366f1"


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class TagOut(TagBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TagAssign(BaseModel):
    tag_id: int
