from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class ClientBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: str = "Active"
    notes: Optional[str] = None
    department_id: Optional[int] = None
    parent_client_id: Optional[int] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    department_id: Optional[int] = None
    parent_client_id: Optional[int] = None
    # Manual override; pass null explicitly to clear back to auto-computed.
    relationship_health: Optional[str] = None


class ClientOut(ClientBase):
    id: int
    relationship_health: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientBulkStatusUpdate(BaseModel):
    client_ids: list[int]
    status: str


class ClientHealth(BaseModel):
    """Rolled-up relationship-health signal for a single client, shown on
    partner-level dashboards. `health` is the manual override when set,
    otherwise the computed value; `computed_health` is always the raw
    computation so the UI can show both."""

    client_id: int
    health: str  # green | amber | red
    computed_health: str
    is_manual_override: bool
    overdue_task_count: int
    open_engagement_count: int
    contracts_expiring_soon: int
    reasons: list[str]
