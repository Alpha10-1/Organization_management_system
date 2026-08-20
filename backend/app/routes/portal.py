import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.notify import notify
from app.core.portal_deps import get_current_active_portal_user
from app.core.storage import get_storage_backend
from app.core.time import utcnow
from app.db.session import get_db
from app.models.file_record import FileRecord
from app.models.milestone import Milestone
from app.models.pbc_request import PBCRequest
from app.models.project import Project
from app.routes.files import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES, UPLOAD_CHUNK_SIZE
from app.schemas.client_portal_user import PortalUserPublic
from app.schemas.milestone import MilestoneOut, MilestoneSignoffRequest
from app.schemas.pbc_request import PBCRequestOut
from app.schemas.portal import PortalEngagementOut, PortalFileOut

router = APIRouter(prefix="/portal", tags=["Client Portal"])

storage = get_storage_backend()

VALID_APPROVAL_STATUSES = {"approved", "rejected"}


def _get_scoped_project(db: Session, portal_user: PortalUserPublic, project_id: int) -> Project:
    """Every portal route that reaches into a specific engagement funnels
    through here so a portal user can never read or act on another
    client's data by guessing a project_id -- the client_id match is the
    entire security boundary for everything below."""
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.client_id == portal_user.client_id,
            Project.deleted_at.is_(None),
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return project


# ---------------------------------------------------------------------------
# Engagements
# ---------------------------------------------------------------------------


@router.get("/engagements", response_model=list[PortalEngagementOut])
def list_my_engagements(
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    return (
        db.query(Project)
        .filter(Project.client_id == portal_user.client_id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
        .all()
    )


@router.get("/engagements/{project_id}", response_model=PortalEngagementOut)
def get_my_engagement(
    project_id: int,
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    return _get_scoped_project(db, portal_user, project_id)


# ---------------------------------------------------------------------------
# Milestones (read + client sign-off)
# ---------------------------------------------------------------------------


@router.get("/engagements/{project_id}/milestones", response_model=list[MilestoneOut])
def list_engagement_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    _get_scoped_project(db, portal_user, project_id)

    return (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id, Milestone.deleted_at.is_(None))
        .order_by(Milestone.due_date.is_(None), Milestone.due_date.asc(), Milestone.created_at.desc())
        .all()
    )


@router.put("/engagements/{project_id}/milestones/{milestone_id}/signoff", response_model=MilestoneOut)
def signoff_milestone_as_client(
    project_id: int,
    milestone_id: int,
    payload: MilestoneSignoffRequest,
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    """The genuine client-side counterpart to PUT /milestones/{id}/signoff
    (which lets staff record a sign-off on the client's behalf, e.g. after
    a phone call). This endpoint is what makes approved_by_email/name on a
    Milestone reflect an actual authenticated client actor rather than a
    staff member typing in the client's name."""
    project = _get_scoped_project(db, portal_user, project_id)

    milestone = (
        db.query(Milestone)
        .filter(Milestone.id == milestone_id, Milestone.project_id == project_id, Milestone.deleted_at.is_(None))
        .first()
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if payload.status not in VALID_APPROVAL_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_APPROVAL_STATUSES)}"
        )

    milestone.approval_status = payload.status
    if payload.status == "approved":
        milestone.approved_at = utcnow()
        milestone.approved_by_email = portal_user.email
        milestone.approved_by_name = portal_user.name
        milestone.rejection_reason = None
    else:  # rejected
        milestone.approved_at = None
        milestone.approved_by_email = portal_user.email
        milestone.approved_by_name = portal_user.name
        milestone.rejection_reason = payload.reason

    db.commit()
    db.refresh(milestone)

    for staff_email in (project.engagement_partner_email, project.engagement_manager_email):
        if staff_email:
            notify(
                db=db,
                user_email=staff_email,
                type="milestone_client_signoff",
                title=f"Client {payload.status} milestone: {milestone.name}",
                body=f"{portal_user.name} {payload.status} '{milestone.name}' on engagement #{project_id}.",
                link=f"/projects/{project_id}",
            )

    return milestone


# ---------------------------------------------------------------------------
# PBC (prepared-by-client) requests
# ---------------------------------------------------------------------------


@router.get("/engagements/{project_id}/pbc-requests", response_model=list[PBCRequestOut])
def list_engagement_pbc_requests(
    project_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    _get_scoped_project(db, portal_user, project_id)

    query = db.query(PBCRequest).filter(PBCRequest.project_id == project_id, PBCRequest.deleted_at.is_(None))
    if status:
        query = query.filter(PBCRequest.status == status)

    return query.order_by(
        PBCRequest.due_date.is_(None), PBCRequest.due_date.asc(), PBCRequest.created_at.asc()
    ).all()


@router.post("/pbc-requests/{pbc_request_id}/upload", response_model=PBCRequestOut)
async def upload_pbc_document(
    pbc_request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    """The client's half of the PBC loop: upload a document against a
    specific requested item. Creates a FileRecord (same table/storage path
    staff uploads use) and moves the request to 'submitted' for staff
    review."""
    pbc_request = (
        db.query(PBCRequest)
        .filter(PBCRequest.id == pbc_request_id, PBCRequest.deleted_at.is_(None))
        .first()
    )
    if not pbc_request:
        raise HTTPException(status_code=404, detail="PBC request not found")

    # Same client_id ownership check as _get_scoped_project, but starting
    # from the request rather than a project_id path param.
    project = (
        db.query(Project)
        .filter(
            Project.id == pbc_request.project_id,
            Project.client_id == portal_user.client_id,
            Project.deleted_at.is_(None),
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="PBC request not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '{extension or 'unknown'}' is not allowed. "
                f"Allowed types: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            ),
        )

    stored_name = f"{uuid.uuid4().hex}{extension}"

    total_size = 0
    try:
        with tempfile.SpooledTemporaryFile(max_size=4 * 1024 * 1024) as buffer:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB upload limit",
                    )
                buffer.write(chunk)
            storage.save(stored_name, buffer)
    finally:
        await file.close()

    record = FileRecord(
        original_name=file.filename,
        stored_name=stored_name,
        file_path=stored_name,
        file_type=file.content_type,
        file_size=total_size,
        client_id=portal_user.client_id,
        project_id=pbc_request.project_id,
        uploaded_by_email=portal_user.email,
        uploaded_by_name=portal_user.name,
    )
    db.add(record)

    pbc_request.status = "submitted"
    pbc_request.submitted_at = utcnow()
    pbc_request.submitted_by_email = portal_user.email
    pbc_request.submitted_by_name = portal_user.name
    # A resubmission (e.g. after rejection) clears the previous review so
    # a stale approval/rejection note doesn't linger next to a new file.
    pbc_request.reviewed_at = None
    pbc_request.reviewed_by_email = None
    pbc_request.reviewed_by_name = None
    pbc_request.review_notes = None

    db.commit()
    db.refresh(record)

    pbc_request.file_id = record.id
    db.commit()
    db.refresh(pbc_request)

    log_activity(
        # log_activity only reads .email/.name off `user`, both of which
        # PortalUserPublic has -- reusing it directly here rather than
        # constructing a throwaway UserPublic-shaped object.
        db=db,
        user=portal_user,
        action="pbc_document_submitted",
        entity_type="pbc_request",
        entity_id=pbc_request.id,
        title=f"Client submitted document: {pbc_request.title}",
        description=f"{portal_user.name} uploaded '{file.filename}' for '{pbc_request.title}'.",
    )

    for staff_email in (project.engagement_partner_email, project.engagement_manager_email):
        if staff_email:
            notify(
                db=db,
                user_email=staff_email,
                type="pbc_submitted",
                title=f"Client submitted: {pbc_request.title}",
                body=f"{portal_user.name} uploaded a document for '{pbc_request.title}' on engagement #{project.id}.",
                link=f"/projects/{project.id}",
            )

    return pbc_request


# ---------------------------------------------------------------------------
# Shared files (read-only view of documents staff have shared on this
# engagement)
# ---------------------------------------------------------------------------


@router.get("/engagements/{project_id}/files", response_model=list[PortalFileOut])
def list_engagement_files(
    project_id: int,
    response: Response,
    db: Session = Depends(get_db),
    portal_user: PortalUserPublic = Depends(get_current_active_portal_user),
):
    _get_scoped_project(db, portal_user, project_id)

    query = db.query(FileRecord).filter(FileRecord.project_id == project_id, FileRecord.deleted_at.is_(None))
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(FileRecord.created_at.desc()).all()
