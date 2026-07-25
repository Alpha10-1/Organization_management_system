import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.client import Client
from app.models.file_record import FileRecord
from app.models.task import Task
from app.schemas.user import UserPublic

router = APIRouter(prefix="/reports", tags=["Reports"])


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_response(title: str, headers: list[str], rows: list[list[str]], filename: str) -> StreamingResponse:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    page_width = pdf.w - 20
    col_width = page_width / max(len(headers), 1)

    pdf.set_font("Helvetica", "B", 9)
    for header in headers:
        pdf.cell(col_width, 8, str(header)[:40], border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for row in rows:
        for cell in row:
            pdf.cell(col_width, 7, str(cell)[:40] if cell is not None else "", border=1)
        pdf.ln()

    output = bytes(pdf.output())
    return StreamingResponse(
        iter([output]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/clients/csv")
def export_clients_csv(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    clients = db.query(Client).filter(Client.deleted_at.is_(None)).order_by(Client.created_at.desc()).all()
    rows = [
        {
            "ID": c.id,
            "First Name": c.first_name,
            "Last Name": c.last_name,
            "Email": c.email or "",
            "Phone": c.phone or "",
            "Status": c.status,
            "Created At": c.created_at.isoformat(),
        }
        for c in clients
    ]
    return _csv_response(rows, "clients.csv")


@router.get("/clients/pdf")
def export_clients_pdf(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    clients = db.query(Client).filter(Client.deleted_at.is_(None)).order_by(Client.created_at.desc()).all()
    headers = ["ID", "First Name", "Last Name", "Email", "Phone", "Status", "Created At"]
    rows = [
        [c.id, c.first_name, c.last_name, c.email or "", c.phone or "", c.status, c.created_at.strftime("%Y-%m-%d")]
        for c in clients
    ]
    return _pdf_response("Client List", headers, rows, "clients.pdf")


@router.get("/files/csv")
def export_files_csv(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    files = db.query(FileRecord).filter(FileRecord.deleted_at.is_(None)).order_by(FileRecord.created_at.desc()).all()
    rows = [
        {
            "ID": f.id,
            "Name": f.original_name,
            "Type": f.file_type or "",
            "Size (bytes)": f.file_size,
            "Version": f.version,
            "Client ID": f.client_id or "",
            "Uploaded By": f.uploaded_by_name,
            "Created At": f.created_at.isoformat(),
        }
        for f in files
    ]
    return _csv_response(rows, "files.csv")


@router.get("/tasks/csv")
def export_tasks_csv(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    tasks = db.query(Task).filter(Task.deleted_at.is_(None)).order_by(Task.created_at.desc()).all()
    rows = [
        {
            "ID": t.id,
            "Title": t.title,
            "Status": t.status,
            "Priority": t.priority,
            "Client ID": t.client_id or "",
            "Assigned To": t.assigned_to_name or "",
            "Due Date": t.due_date.isoformat() if t.due_date else "",
            "Created At": t.created_at.isoformat(),
        }
        for t in tasks
    ]
    return _csv_response(rows, "tasks.csv")


@router.get("/activity-logs/csv")
def export_activity_logs_csv(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(2000).all()
    rows = [
        {
            "ID": a.id,
            "Action": a.action,
            "Entity Type": a.entity_type,
            "Entity ID": a.entity_id or "",
            "Title": a.title,
            "User": a.user_name,
            "Email": a.user_email,
            "Date": a.created_at.isoformat(),
        }
        for a in logs
    ]
    return _csv_response(rows, "activity_logs.csv")
