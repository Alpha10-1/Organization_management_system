import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.file_access import can_delete_file, can_view_file
from app.db.session import get_db
from app.models.client import Client
from app.models.file_record import FileRecord
from app.schemas.file_record import FileRecordOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=list[FileRecordOut])
def list_files(
    search: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    client_id: int | None = Query(default=None),
    mine_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(FileRecord)

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

    records = query.order_by(FileRecord.created_at.desc()).all()

    visible_records = [record for record in records if can_view_file(current_user, record)]
    return visible_records


@router.post("/upload", response_model=FileRecordOut)
async def upload_file(
    file: UploadFile = File(...),
    client_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    extension = Path(file.filename).suffix
    stored_name = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    log_activity(
        db=db,
        user=current_user,
        action="file_uploaded",
        entity_type="file",
        entity_id=record.id,
        title=f"File uploaded: {record.original_name}",
        description=f"Uploaded file '{record.original_name}'",
    )

    return record


@router.get("/{file_id}", response_model=FileRecordOut)
def get_file_record(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

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
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

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
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_delete_file(current_user, record):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this file")

    stored_path = record.file_path
    original_name = record.original_name

    db.delete(record)
    db.commit()

    if os.path.exists(stored_path):
        os.remove(stored_path)

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