from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.department_scope import require_scoped_write
from app.core.deps import get_current_active_user
from app.core.pipeline import require_valid_prospect_transition, validate_prospect_status
from app.core.time import utcnow
from app.db.session import get_db
from app.models.client import Client
from app.models.department import Department
from app.models.prospect import PROSPECT_SOURCES, PROSPECT_STATUSES, Prospect, ProspectStageEvent
from app.models.proposal import Proposal
from app.models.user import User
from app.schemas.prospect import (
    PipelineSummaryOut,
    PipelineSummaryStage,
    ProspectConvertRequest,
    ProspectCreate,
    ProspectOut,
    ProspectStageEventOut,
    ProspectStatusUpdate,
    ProspectUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/prospects", tags=["CRM / Pipeline"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200


def _validate_source(source: str) -> None:
    if source not in PROSPECT_SOURCES:
        raise HTTPException(status_code=400, detail=f"Invalid source. Must be one of: {sorted(PROSPECT_SOURCES)}")


def _resolve_assignee(db: Session, user_id: int | None) -> tuple[str | None, str | None]:
    if user_id is None:
        return None, None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Assigned user not found")
    return user.email, user.name


@router.get("/", response_model=list[ProspectOut])
def list_prospects(
    response: Response,
    status: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    assigned_to_user_id: int | None = Query(default=None),
    source: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Prospect).filter(Prospect.deleted_at.is_(None))

    if status:
        query = query.filter(Prospect.status == status)
    if department_id is not None:
        query = query.filter(Prospect.department_id == department_id)
    if assigned_to_user_id is not None:
        query = query.filter(Prospect.assigned_to_user_id == assigned_to_user_id)
    if source:
        query = query.filter(Prospect.source == source)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(Prospect.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/pipeline-summary", response_model=PipelineSummaryOut)
def get_pipeline_summary(
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Funnel view of the whole pipeline: how many prospects (and how much
    estimated value) sit at each stage right now, plus the firm's overall
    win rate among prospects that have reached a terminal outcome."""
    query = db.query(Prospect).filter(Prospect.deleted_at.is_(None))
    if department_id is not None:
        query = query.filter(Prospect.department_id == department_id)

    prospects = query.all()

    stages: list[PipelineSummaryStage] = []
    for status_value in PROSPECT_STATUSES:
        in_stage = [p for p in prospects if p.status == status_value]
        stages.append(
            PipelineSummaryStage(
                status=status_value,
                count=len(in_stage),
                total_estimated_value=sum((p.estimated_value or Decimal(0)) for p in in_stage) or Decimal(0),
            )
        )

    won_count = sum(1 for p in prospects if p.status == "won")
    lost_count = sum(1 for p in prospects if p.status == "lost")
    decided = won_count + lost_count
    win_rate = round((won_count / decided) * 100, 1) if decided else None

    open_pipeline_value = sum(
        (p.estimated_value or Decimal(0)) for p in prospects if p.status not in ("won", "lost")
    ) or Decimal(0)

    return PipelineSummaryOut(
        stages=stages,
        won_count=won_count,
        lost_count=lost_count,
        win_rate_percent=win_rate,
        open_pipeline_value=open_pipeline_value,
    )


@router.post("/", response_model=ProspectOut)
def create_prospect(
    payload: ProspectCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    _validate_source(payload.source)

    if payload.department_id is not None:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")

    require_scoped_write(db, current_user, payload.department_id)

    assigned_email, assigned_name = _resolve_assignee(db, payload.assigned_to_user_id)

    prospect = Prospect(
        **payload.model_dump(),
        assigned_to_email=assigned_email,
        assigned_to_name=assigned_name,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    log_activity(
        db=db,
        user=current_user,
        action="prospect_created",
        entity_type="prospect",
        entity_id=prospect.id,
        title=f"Prospect added: {prospect.name}",
        description=f"New prospect from source '{prospect.source}'.",
    )

    return prospect


@router.get("/{prospect_id}", response_model=ProspectOut)
def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect


@router.put("/{prospect_id}", response_model=ProspectOut)
def update_prospect(
    prospect_id: int,
    payload: ProspectUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    updates = payload.model_dump(exclude_unset=True)

    require_scoped_write(db, current_user, prospect.department_id)
    if "department_id" in updates and updates["department_id"] != prospect.department_id:
        require_scoped_write(db, current_user, updates["department_id"])
        if updates["department_id"] is not None:
            dept = db.query(Department).filter(Department.id == updates["department_id"]).first()
            if not dept:
                raise HTTPException(status_code=404, detail="Department not found")

    if "source" in updates:
        _validate_source(updates["source"])

    if "assigned_to_user_id" in updates:
        assigned_email, assigned_name = _resolve_assignee(db, updates["assigned_to_user_id"])
        updates["assigned_to_email"] = assigned_email
        updates["assigned_to_name"] = assigned_name

    for key, value in updates.items():
        setattr(prospect, key, value)

    db.commit()
    db.refresh(prospect)

    log_activity(
        db=db,
        user=current_user,
        action="prospect_updated",
        entity_type="prospect",
        entity_id=prospect.id,
        title=f"Prospect updated: {prospect.name}",
        description="Prospect record updated.",
    )

    return prospect


@router.patch("/{prospect_id}/status", response_model=ProspectOut)
def update_prospect_status(
    prospect_id: int,
    payload: ProspectStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    require_scoped_write(db, current_user, prospect.department_id)

    require_valid_prospect_transition(prospect.status, payload.status)

    if payload.status == "lost" and not (payload.notes and payload.notes.strip()):
        raise HTTPException(status_code=400, detail="notes (lost_reason) is required when marking a prospect lost")

    if payload.status == "won":
        has_accepted_proposal = (
            db.query(Proposal)
            .filter(
                Proposal.prospect_id == prospect.id,
                Proposal.status == "accepted",
                Proposal.deleted_at.is_(None),
            )
            .first()
        )
        if not has_accepted_proposal:
            raise HTTPException(
                status_code=400,
                detail="A prospect can only be marked won once it has an accepted proposal",
            )

    from_status = prospect.status
    prospect.status = payload.status
    if payload.status == "lost":
        prospect.lost_reason = payload.notes

    db.add(
        ProspectStageEvent(
            prospect_id=prospect.id,
            from_status=from_status,
            to_status=payload.status,
            notes=payload.notes,
            actor_email=current_user.email,
            actor_name=current_user.name,
        )
    )

    db.commit()
    db.refresh(prospect)

    log_activity(
        db=db,
        user=current_user,
        action="prospect_status_changed",
        entity_type="prospect",
        entity_id=prospect.id,
        title=f"Prospect stage changed: {prospect.name}",
        description=f"Moved from '{from_status}' to '{payload.status}'.",
    )

    return prospect


@router.get("/{prospect_id}/stage-history", response_model=list[ProspectStageEventOut])
def get_prospect_stage_history(
    prospect_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    return (
        db.query(ProspectStageEvent)
        .filter(ProspectStageEvent.prospect_id == prospect_id)
        .order_by(ProspectStageEvent.created_at.asc())
        .all()
    )


@router.post("/{prospect_id}/convert", response_model=ProspectOut)
def convert_prospect(
    prospect_id: int,
    payload: ProspectConvertRequest = ProspectConvertRequest(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Turns a won prospect into a real Client record -- the moment the
    BD pipeline hands off to engagement delivery. Engagements themselves
    are still created the normal way afterward (POST /projects/), since a
    won deal might spin up more than one engagement over time.
    """
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    if prospect.status != "won":
        raise HTTPException(status_code=400, detail="Only a 'won' prospect can be converted to a client")
    if prospect.converted_client_id is not None:
        raise HTTPException(status_code=400, detail="This prospect has already been converted to a client")

    require_scoped_write(db, current_user, prospect.department_id)

    client_type = payload.client_type or ("business" if prospect.company_name else "individual")
    if client_type not in ("business", "individual", "npo"):
        raise HTTPException(status_code=400, detail="client_type must be one of: business, individual, npo")

    company_name = payload.company_name or prospect.company_name
    first_name = payload.first_name
    last_name = payload.last_name

    if client_type == "individual" and (not first_name or not last_name):
        parts = prospect.name.strip().split(" ", 1)
        first_name = first_name or parts[0]
        last_name = last_name or (parts[1] if len(parts) > 1 else parts[0])

    if client_type in ("business", "npo") and not company_name:
        company_name = prospect.name

    new_client = Client(
        client_type=client_type,
        first_name=first_name,
        last_name=last_name,
        company_name=company_name,
        industry=prospect.industry,
        website=prospect.website,
        phone=prospect.contact_phone,
        email=prospect.contact_email,
        status="Active",
        department_id=prospect.department_id,
        notes=prospect.notes,
    )
    db.add(new_client)
    db.flush()  # assign new_client.id before linking it back to the prospect

    prospect.converted_client_id = new_client.id
    prospect.converted_at = utcnow()

    db.commit()
    db.refresh(prospect)

    log_activity(
        db=db,
        user=current_user,
        action="prospect_converted",
        entity_type="prospect",
        entity_id=prospect.id,
        title=f"Prospect converted to client: {prospect.name}",
        description=f"Created client #{new_client.id} ('{new_client.display_name}') from this won prospect.",
    )

    return prospect


@router.delete("/{prospect_id}")
def delete_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.deleted_at.is_(None)).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    require_scoped_write(db, current_user, prospect.department_id)

    prospect.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="prospect_deleted",
        entity_type="prospect",
        entity_id=prospect.id,
        title=f"Prospect deleted: {prospect.name}",
        description="Prospect record soft-deleted.",
    )

    return {"detail": "Prospect deleted"}
