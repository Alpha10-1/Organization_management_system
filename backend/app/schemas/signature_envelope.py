from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class SendForSignatureRequest(BaseModel):
    signer_email: EmailStr
    signer_name: str


class SignatureEnvelopeOut(BaseModel):
    id: int
    document_type: str
    document_id: int
    project_id: int
    provider: str
    provider_envelope_id: str
    signer_email: str
    signer_name: str
    status: str
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    requested_by_email: str
    requested_by_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EsignWebhookPayload(BaseModel):
    provider_envelope_id: str
    # completed | declined | voided
    status: str
    reason: Optional[str] = None
