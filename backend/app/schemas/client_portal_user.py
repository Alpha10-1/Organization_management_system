from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class ClientPortalUserInvite(BaseModel):
    name: str
    email: EmailStr
    client_contact_id: Optional[int] = None


class ClientPortalUserUpdate(BaseModel):
    name: Optional[str] = None
    disabled: Optional[bool] = None


class ClientPortalUserOut(BaseModel):
    id: int
    client_id: int
    client_contact_id: Optional[int] = None
    name: str
    email: str
    disabled: bool
    invited_by_email: str
    invited_by_name: str
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalUserPublic(BaseModel):
    """The client-portal equivalent of UserPublic -- returned by
    /portal/auth/me and embedded wherever a portal-authenticated request
    needs to know who's calling."""

    id: int
    client_id: int
    name: str
    email: EmailStr
    disabled: bool = False
