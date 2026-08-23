from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.department_scope import require_scoped_write
from app.core.deps import get_current_active_user
from app.core.pipeline import require_valid_proposal_transition
from app.core.time import utcnow
from app.db.session import get_db
from app.models.prospect import Prospect
from app.models.proposal import Proposal
from app.schemas.proposal import (
    ProposalCreate,
    ProposalOut,
    ProposalStatusUpdate,
    ProposalUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/proposals", tags=["CRM / Pipeline"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200


def _get_prospect(db: Session, prospect_id: int) -> Prospect:
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect


@router.get("/", response_model=list[ProposalOut])
def list_proposals(
    response: Response,
    prospect_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Proposal).filter(Proposal.deleted_at.is_(None))

    if prospect_id is not None:
        query = query.filter(Proposal.prospect_id == prospect_id)
    if status:
        query = query.filter(Proposal.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ProposalOut)
def create_proposal(
    payload: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    prospect = _get_prospect(db, payload.prospect_id)

    if prospect.status in ("won", "lost"):
        raise HTTPException(status_code=400, detail="Cannot add a proposal to a prospect that's already closed")

    require_scoped_write(db, current_user, prospect.department_id)

    proposal = Proposal(
        **payload.model_dump(),
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    log_activity(
        db=db,
        user=current_user,
        action="proposal_created",
        entity_type="proposal",
        entity_id=proposal.id,
        title=f"Proposal drafted: {proposal.title}",
        description=f"New proposal for prospect #{prospect.id} ('{prospect.name}').",
    )

    return proposal


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.deleted_at.is_(None)).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.put("/{proposal_id}", response_model=ProposalOut)
def update_proposal(
    proposal_id: int,
    payload: ProposalUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.deleted_at.is_(None)).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    prospect = _get_prospect(db, proposal.prospect_id)
    require_scoped_write(db, current_user, prospect.department_id)

    if proposal.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft proposal can be edited; use status transitions otherwise")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(proposal, key, value)

    db.commit()
    db.refresh(proposal)

    log_activity(
        db=db,
        user=current_user,
        action="proposal_updated",
        entity_type="proposal",
        entity_id=proposal.id,
        title=f"Proposal updated: {proposal.title}",
        description="Proposal record updated.",
    )

    return proposal


@router.patch("/{proposal_id}/status", response_model=ProposalOut)
def update_proposal_status(
    proposal_id: int,
    payload: ProposalStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.deleted_at.is_(None)).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    prospect = _get_prospect(db, proposal.prospect_id)
    require_scoped_write(db, current_user, prospect.department_id)

    require_valid_proposal_transition(proposal.status, payload.status)

    from_status = proposal.status
    proposal.status = payload.status

    if payload.status in ("accepted", "rejected", "expired"):
        proposal.decided_at = utcnow()
        proposal.decided_by_email = current_user.email
        proposal.decided_by_name = current_user.name
        proposal.decision_notes = payload.notes

    if payload.status == "sent" and proposal.sent_date is None:
        proposal.sent_date = utcnow().date()

    db.commit()
    db.refresh(proposal)

    log_activity(
        db=db,
        user=current_user,
        action="proposal_status_changed",
        entity_type="proposal",
        entity_id=proposal.id,
        title=f"Proposal status changed: {proposal.title}",
        description=f"Moved from '{from_status}' to '{payload.status}' (prospect #{prospect.id}).",
    )

    return proposal


@router.delete("/{proposal_id}")
def delete_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.deleted_at.is_(None)).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    prospect = _get_prospect(db, proposal.prospect_id)
    require_scoped_write(db, current_user, prospect.department_id)

    proposal.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="proposal_deleted",
        entity_type="proposal",
        entity_id=proposal.id,
        title=f"Proposal deleted: {proposal.title}",
        description="Proposal record soft-deleted.",
    )

    return {"detail": "Proposal deleted"}
