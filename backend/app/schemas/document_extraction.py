from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentAmount(BaseModel):
    label: str
    value: str
    context: str


class DocumentExtractionOut(BaseModel):
    id: int
    file_record_id: int
    status: str  # success | unsupported_type | empty | error
    amounts: list[DocumentAmount] = []
    dates: list[str] = []
    labeled_figures: dict[str, str] = {}
    excerpt: Optional[str] = None
    extracted_by_email: str
    extracted_by_name: str
    extracted_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
