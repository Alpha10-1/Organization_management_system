from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.independence import check_conflicts
from app.core.time import utcnow
from app.db.session import get_db
from app.models.client import Client
from app.models.independence import ConflictOverride, IndependenceDisclosure
from app.models.project import Project
from app.models.user import User
from app.schemas.independence import (
    ConflictCheckOut,
    ConflictOverrideCreate,
    ConflictOverrideOut,
    IndependenceDisclosureCreate,
    IndependenceDisclosureOut,
    IndependenceDisclosureUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/independence", tags=["Independence & Conflicts"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_TYPES = {"financial_interest", "family_relationship", "prior_employment", "other"}
VALID_STATUSES = {"active", "resolved"}


def _override_out(override: ConflictOverride) -> ConflictOverrideOut:
    ids = [int(x) for x in override.disclosure_ids.split(",") if x.strip()]
    return ConflictOverrideOut(
        id=override.id,
        project_id=override.project_id,
        user_id=override.user_id,
        client_id=override.client_id,
        disclosure_ids=ids,
        reason=override.reason,
        overridden_by_email=override.overridden_by_email,
        overridden_by_name=override.overridden_by_name,
        created_at=override.created_at,
    )


@router.get("/disclosures", response_model=list[IndependenceDisclosureOut])
def list_disclosures(
    response: Response,
    user_id: int | None = Query(default=None),
    client_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Disclosures are personal/financial data, so unlike most list
    endpoints in this app, reads are restricted: non-admins only ever see
    their own disclosures, regardless of what user_id is passed."""
    query = db.query(IndependenceDisclosure).filter(IndependenceDisclosure.deleted_at.is_(None))

    if current_user.role != "admin":
        query = query.filter(IndependenceDisclosure.user_id == current_user.id)
    elif user_id is not None:
        query = query.filter(IndependenceDisclosure.user_id == user_id)

    if client_id is not None:
        query = query.filter(IndependenceDisclosure.client_id == client_id)
    if status:
        query = query.filter(IndependenceDisclosure.status == status)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(IndependenceDisclosure.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/disclosures", response_model=IndependenceDisclosureOut)
def create_disclosure(
    payload: IndependenceDisclosureCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.disclosure_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid disclosure_type. Must be one of: {sorted(VALID_TYPES)}")

    target_user_id = payload.user_id or current_user.id
    if target_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can log a disclosure on someone else's behalf")

    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.client_id is not None:
        client = db.query(Client).filter(Client.id == payload.client_id, Client.deleted_at.is_(None)).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    disclosure = IndependenceDisclosure(
        user_id=target_user_id,
        client_id=payload.client_id,
        disclosure_type=payload.disclosure_type,
        description=payload.description,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(disclosure)
    db.commit()
    db.refresh(disclosure)

    log_activity(
        db=db,
        user=current_user,
        action="independence_disclosure_created",
        entity_type="independence_disclosure",
        entity_id=disclosure.id,
        title=f"Independence disclosure logged for {user.name}",
        description=f"{payload.disclosure_type} disclosure logged" + (f" against client #{payload.client_id}." if payload.client_id else " (general)."),
    )

    return disclosure


@router.put("/disclosures/{disclosure_id}", response_model=IndependenceDisclosureOut)
def update_disclosure(
    disclosure_id: int,
    payload: IndependenceDisclosureUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    disclosure = (
        db.query(IndependenceDisclosure)
        .filter(IndependenceDisclosure.id == disclosure_id, IndependenceDisclosure.deleted_at.is_(None))
        .first()
    )
    if not disclosure:
        raise HTTPException(status_code=404, detail="Disclosure not found")

    if disclosure.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only update your own disclosures")

    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")

    for key, value in updates.items():
        setattr(disclosure, key, value)

    if updates.get("status") == "resolved" and disclosure.resolved_at is None:
        disclosure.resolved_at = utcnow()
        disclosure.resolved_by_email = current_user.email
        disclosure.resolved_by_name = current_user.name
    elif updates.get("status") == "active":
        disclosure.resolved_at = None
        disclosure.resolved_by_email = None
        disclosure.resolved_by_name = None

    db.commit()
    db.refresh(disclosure)

    log_activity(
        db=db,
        user=current_user,
        action="independence_disclosure_updated",
        entity_type="independence_disclosure",
        entity_id=disclosure.id,
        title="Independence disclosure updated",
        description=f"Disclosure #{disclosure.id} updated.",
    )

    return disclosure


@router.delete("/disclosures/{disclosure_id}")
def delete_disclosure(
    disclosure_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    disclosure = (
        db.query(IndependenceDisclosure)
        .filter(IndependenceDisclosure.id == disclosure_id, IndependenceDisclosure.deleted_at.is_(None))
        .first()
    )
    if not disclosure:
        raise HTTPException(status_code=404, detail="Disclosure not found")

    if disclosure.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only remove your own disclosures")

    disclosure.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="independence_disclosure_deleted",
        entity_type="independence_disclosure",
        entity_id=disclosure_id,
        title="Independence disclosure deleted",
        description=f"Disclosure #{disclosure_id} removed (soft delete).",
    )

    return {"message": "Disclosure deleted successfully"}


@router.get("/check", response_model=ConflictCheckOut)
def run_conflict_check(
    user_id: int = Query(...),
    client_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Ad hoc check used by the staffing UI before submitting a project
    assignment, so a conflict can be surfaced to the person doing the
    staffing before they hit submit (the assignment endpoint itself
    enforces this too -- see app.routes.projects.add_project_assignment)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    disclosures = check_conflicts(db, user_id, client_id)

    return ConflictCheckOut(
        user_id=user_id,
        client_id=client_id,
        has_conflict=bool(disclosures),
        disclosures=disclosures,
    )


@router.get("/overrides", response_model=list[ConflictOverrideOut])
def list_overrides(
    response: Response,
    project_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(ConflictOverride)
    if project_id is not None:
        query = query.filter(ConflictOverride.project_id == project_id)
    if user_id is not None:
        query = query.filter(ConflictOverride.user_id == user_id)

    response.headers["X-Total-Count"] = str(query.count())

    overrides = query.order_by(ConflictOverride.created_at.desc()).offset(skip).limit(limit).all()
    return [_override_out(o) for o in overrides]


@router.post("/overrides", response_model=ConflictOverrideOut)
def create_override(
    payload: ConflictOverrideCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Explicit standalone override endpoint, kept for completeness /
    scripted use -- day to day this is normally exercised implicitly by
    passing conflict_override_reason to POST /projects/{id}/assignments,
    which calls the same logic inline so the override and the assignment
    it enables are created atomically."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can override an independence conflict")

    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=400, detail="An override reason is required")

    disclosures = check_conflicts(db, payload.user_id, project.client_id)
    if not disclosures:
        raise HTTPException(status_code=400, detail="No active conflicts found to override")

    override = ConflictOverride(
        project_id=project.id,
        user_id=payload.user_id,
        client_id=project.client_id,
        disclosure_ids=",".join(str(d.id) for d in disclosures),
        reason=payload.reason,
        overridden_by_email=current_user.email,
        overridden_by_name=current_user.name,
    )
    db.add(override)
    db.commit()
    db.refresh(override)

    log_activity(
        db=db,
        user=current_user,
        action="independence_conflict_overridden",
        entity_type="project",
        entity_id=project.id,
        title=f"Independence conflict overridden: {project.name}",
        description=f"Staffed user #{payload.user_id} on '{project.name}' despite {len(disclosures)} active conflict(s). Reason: {payload.reason}",
    )

    return _override_out(override)
