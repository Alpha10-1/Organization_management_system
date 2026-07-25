import io
import os
import uuid
import zipfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.file_access import can_delete_file, can_view_file
from app.core.time import utcnow
from app.db.session import get_db
from app.models.client import Client
from app.models.file_record import FileRecord
from app.schemas.file_record import FileRecordOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/files", tags=["Files"])


class BulkFileIds(BaseModel):
    file_ids: list[int]

# Resolve relative to the backend package (not the process's cwd) so
# uploads land in the same place regardless of where uvicorn is launched
# from. Override with UPLOAD_DIR to point at a different volume/mount.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(_BACKEND_ROOT / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200

# Configurable so deployments can tighten/loosen without a code change
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25")) * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024  # read/write 1MB at a time

# Deliberately excludes executables/scripts (.exe, .sh, .js, .php, ...).
# Extend this list if the org needs to store other document types.
ALLOWED_UPLOAD_EXTENSIONS = {
    # images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff",
    # documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".rtf",
}


@router.get("/", response_model=list[FileRecordOut])
def list_files(
    response: Response,
    search: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    client_id: int | None = Query(default=None),
    mine_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(FileRecord).filter(FileRecord.deleted_at.is_(None))

    if current_user.role == "staff" and mine_only:
        query = query.filter(FileRecord.uploaded_by_email == current_user.email)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                FileRecord.original_name.ilike(search_term),
                FileRecord.file_type.ilike(search_term),
                FileRecord.uploaded_by_name.ilike(search_term),
                FileRecord.uploaded_by_email.ilike(search_term),
            )
        )

    if file_type:
        query = query.filter(FileRecord.file_type == file_type)

    if client_id is not None:
        query = query.filter(FileRecord.client_id == client_id)

    response.headers["X-Total-Count"] = str(query.count())

    # NOTE: can_view_file() currently allows both admin and staff to view
    # every file, so pagination at the SQL level below is safe today. If
    # can_view_file() is ever changed to hide records per-user, this
    # filter-after-paginate order would need to move before the offset/limit
    # (e.g. by pushing visibility into the query itself).
    records = (
        query.order_by(FileRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    visible_records = [record for record in records if can_view_file(current_user, record)]
    return visible_records


@router.post("/upload", response_model=FileRecordOut)
async def upload_file(
    file: UploadFile = File(...),
    client_id: int | None = Form(default=None),
    replaces_file_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    previous_version = None
    if replaces_file_id is not None:
        previous_version = (
            db.query(FileRecord)
            .filter(FileRecord.id == replaces_file_id, FileRecord.deleted_at.is_(None))
            .first()
        )
        if not previous_version:
            raise HTTPException(status_code=404, detail="File to replace not found")
        if not can_delete_file(current_user, previous_version):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to upload a new version of this file",
            )
        if client_id is None:
            client_id = previous_version.client_id

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '{extension or 'unknown'}' is not allowed. "
                f"Allowed types: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            ),
        )

    if client_id is not None:
        client = (
            db.query(Client)
            .filter(Client.id == client_id, Client.deleted_at.is_(None))
            .first()
        )
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    stored_name = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_name

    total_size = 0
    try:
        with file_path.open("wb") as buffer:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            "File exceeds the "
                            f"{MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB upload limit"
                        ),
                    )
                buffer.write(chunk)
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    file_size = file_path.stat().st_size

    record = FileRecord(
        original_name=file.filename,
        stored_name=stored_name,
        file_path=str(file_path),
        file_type=file.content_type,
        file_size=file_size,
        client_id=client_id,
        uploaded_by_email=current_user.email,
        uploaded_by_name=current_user.name,
        version=(previous_version.version + 1) if previous_version else 1,
        previous_version_id=previous_version.id if previous_version else None,
    )

    db.add(record)

    if previous_version:
        # The old version is kept on disk and in the DB for history, but
        # hidden from the normal (current-files) list -- get_file_versions
        # below can still walk the chain.
        previous_version.deleted_at = utcnow()

    db.commit()
    db.refresh(record)

    log_activity(
        db=db,
        user=current_user,
        action="file_uploaded",
        entity_type="file",
        entity_id=record.id,
        title=f"File uploaded: {record.original_name}",
        description=(
            f"Uploaded version {record.version} of '{record.original_name}'"
            if previous_version
            else f"Uploaded file '{record.original_name}'"
        ),
    )

    return record


@router.get("/{file_id}", response_model=FileRecordOut)
def get_file_record(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id, FileRecord.deleted_at.is_(None))
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_view_file(current_user, record):
        raise HTTPException(status_code=403, detail="You do not have access to this file")

    return record


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id, FileRecord.deleted_at.is_(None))
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_view_file(current_user, record):
        raise HTTPException(status_code=403, detail="You do not have access to this file")

    if not os.path.exists(record.file_path):
        raise HTTPException(status_code=404, detail="Stored file missing")

    log_activity(
        db=db,
        user=current_user,
        action="file_downloaded",
        entity_type="file",
        entity_id=record.id,
        title=f"File downloaded: {record.original_name}",
        description=f"Downloaded file '{record.original_name}'",
    )

    return FileResponse(
        path=record.file_path,
        filename=record.original_name,
        media_type=record.file_type or "application/octet-stream",
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id, FileRecord.deleted_at.is_(None))
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_delete_file(current_user, record):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this file")

    original_name = record.original_name

    # Soft delete: the row and the file on disk are both kept for
    # recovery/audit; deletion just hides the record from normal queries.
    record.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="file_deleted",
        entity_type="file",
        entity_id=file_id,
        title=f"File deleted: {original_name}",
        description=f"Deleted file '{original_name}'",
    )

    return {"message": "File deleted successfully"}


@router.get("/{file_id}/versions", response_model=list[FileRecordOut])
def get_file_versions(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Walk the previous_version_id chain in both directions to return the
    full version history for a file, newest first."""
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_view_file(current_user, record):
        raise HTTPException(status_code=403, detail="You do not have access to this file")

    # Walk backwards to the oldest ancestor
    oldest = record
    while oldest.previous_version_id:
        parent = db.query(FileRecord).filter(FileRecord.id == oldest.previous_version_id).first()
        if not parent:
            break
        oldest = parent

    # Walk forwards from the oldest, collecting every version
    chain = [oldest]
    current = oldest
    while True:
        child = db.query(FileRecord).filter(FileRecord.previous_version_id == current.id).first()
        if not child:
            break
        chain.append(child)
        current = child

    return list(reversed(chain))


@router.post("/bulk/delete")
def bulk_delete_files(
    payload: BulkFileIds,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if not payload.file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")

    records = (
        db.query(FileRecord)
        .filter(FileRecord.id.in_(payload.file_ids), FileRecord.deleted_at.is_(None))
        .all()
    )

    deleted = 0
    for record in records:
        if not can_delete_file(current_user, record):
            continue
        record.deleted_at = utcnow()
        deleted += 1

    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="file_bulk_deleted",
        entity_type="file",
        title=f"Bulk delete: {deleted} file(s)",
        description=f"Deleted {deleted} file(s) in bulk.",
    )

    return {"message": f"Deleted {deleted} file(s)", "deleted": deleted, "skipped": len(records) - deleted}


@router.post("/bulk/download")
def bulk_download_files(
    payload: BulkFileIds,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if not payload.file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")

    records = (
        db.query(FileRecord)
        .filter(FileRecord.id.in_(payload.file_ids), FileRecord.deleted_at.is_(None))
        .all()
    )

    visible = [r for r in records if can_view_file(current_user, r)]
    if not visible:
        raise HTTPException(status_code=404, detail="No accessible files found for the given IDs")

    buffer = io.BytesIO()
    used_names: dict[str, int] = {}

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for record in visible:
            if not os.path.exists(record.file_path):
                continue
            name = record.original_name
            count = used_names.get(name, 0)
            used_names[name] = count + 1
            if count:
                stem, dot, ext = name.rpartition(".")
                name = f"{stem} ({count}).{ext}" if dot else f"{name} ({count})"
            zip_file.write(record.file_path, arcname=name)

    buffer.seek(0)

    log_activity(
        db=db,
        user=current_user,
        action="file_bulk_downloaded",
        entity_type="file",
        title=f"Bulk download: {len(visible)} file(s)",
        description=f"Downloaded {len(visible)} file(s) as a zip archive.",
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="files.zip"'},
    )