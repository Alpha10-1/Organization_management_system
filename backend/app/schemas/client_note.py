from datetime import datetime

from pydantic import BaseModel


class ClientNoteCreate(BaseModel):
    body: str


class ClientNoteOut(BaseModel):
    id: int
    client_id: int
    author_email: str
    author_name: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}
