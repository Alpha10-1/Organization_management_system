from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.config import settings
from app.core.notify import notify
from app.core.time import utcnow
from app.db.session import get_db
from app.models.change_order import ChangeOrder
from app.models.contract import Contract
from app.models.signature_envelope import SignatureEnvelope
from app.schemas.signature_envelope import EsignWebhookPayload, SignatureEnvelopeOut

router = APIRouter(prefix="/esign", tags=["E-Signature"])

VALID_WEBHOOK_STATUSES = {"completed", "declined", "voided"}


class _SystemActor:
    email = "system@internal"
    name = "E-Signature Provider"


_SYSTEM_ACTOR = _SystemActor()


@router.post("/webhook", response_model=SignatureEnvelopeOut)
def esign_webhook(
    payload: EsignWebhookPayload,
    db: Session = Depends(get_db),
    x_esign_webhook_secret: str | None = Header(default=None),
):
    """Provider callback (DocuSign Connect, or the mock backend's own
    test helper hitting this directly) that resolves a signature outcome
    back to the underlying Contract or ChangeOrder.

    Deliberately not behind get_current_active_user -- the caller is the
    e-sign provider's server, not a logged-in person. The shared-secret
    header is what stands in for auth here, same purpose a DocuSign
    Connect HMAC key or webhook signing secret serves in a real
    integration."""
    if x_esign_webhook_secret != settings.ESIGN_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    if payload.status not in VALID_WEBHOOK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_WEBHOOK_STATUSES)}")

    envelope = (
        db.query(SignatureEnvelope)
        .filter(
            SignatureEnvelope.provider_envelope_id == payload.provider_envelope_id,
            SignatureEnvelope.deleted_at.is_(None),
        )
        .first()
    )
    if not envelope:
        raise HTTPException(status_code=404, detail="Signature envelope not found")

    if envelope.status != "sent":
        raise HTTPException(status_code=400, detail=f"Envelope is already '{envelope.status}', not awaiting a callback")

    envelope.status = payload.status
    if payload.status == "completed":
        envelope.completed_at = utcnow()
    elif payload.status == "declined":
        envelope.declined_at = utcnow()
        envelope.decline_reason = payload.reason
    else:  # voided
        envelope.voided_at = utcnow()
        envelope.void_reason = payload.reason

    _apply_to_document(db, envelope)

    db.commit()
    db.refresh(envelope)

    log_activity(
        db=db,
        # No authenticated person originates a webhook call -- log it as
        # a system actor rather than passing None through log_activity
        # (which unconditionally reads user.email/user.name).
        user=_SYSTEM_ACTOR,
        action="esign_envelope_updated",
        entity_type=envelope.document_type,
        entity_id=envelope.document_id,
        title=f"Signature {payload.status}: {envelope.document_type} #{envelope.document_id}",
        description=f"{envelope.signer_name} ({envelope.signer_email}) -- {payload.status}."
        + (f" {payload.reason}" if payload.reason else ""),
    )

    return envelope


def _apply_to_document(db: Session, envelope: SignatureEnvelope) -> None:
    """Push a terminal envelope status onto the Contract or ChangeOrder it
    belongs to, and notify whoever originally sent it."""
    if envelope.document_type == "contract":
        contract = db.query(Contract).filter(Contract.id == envelope.document_id).first()
        if contract and envelope.status == "completed":
            contract.status = "signed"
            contract.signed_date = utcnow().date()
    elif envelope.document_type == "change_order":
        change_order = db.query(ChangeOrder).filter(ChangeOrder.id == envelope.document_id).first()
        if change_order:
            change_order.signature_status = envelope.status
            if envelope.status == "completed":
                change_order.signed_at = utcnow().date()

    notify(
        db=db,
        user_email=envelope.requested_by_email,
        type="esign_envelope_updated",
        title=f"Signature {envelope.status}: {envelope.document_type.replace('_', ' ')} #{envelope.document_id}",
        body=f"{envelope.signer_name} {envelope.status} the {envelope.document_type.replace('_', ' ')}.",
    )
