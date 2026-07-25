from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CommentCreate(BaseModel):
    entity_type: str
    entity_id: int
    body: str


class CommentOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    author_email: str
    author_name: str
    body: str
    mentions: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
