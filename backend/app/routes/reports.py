import csv
import io
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.core.client_health import compute_client_health
from app.core.deps import get_current_active_user
from app.core.time import utcnow
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.client import Client
from app.models.contract import Contract
from app.models.file_record import FileRecord
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.task import Task
from app.models.time_entry import TimeEntry
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
            "Type": c.client_type,
            "Name": c.display_name,
            "Company Name": c.company_name or "",
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
    headers = ["ID", "Type", "Name", "Company Name", "Email", "Phone", "Status", "Created At"]
    rows = [
        [c.id, c.client_type, c.display_name, c.company_name or "", c.email or "", c.phone or "", c.status, c.created_at.strftime("%Y-%m-%d")]
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


# --- Dashboards ------------------------------------------------------------


@router.get("/dashboard/partner")
def partner_dashboard(
    partner_email: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Read-layer rollup for a partner: their active engagements, upcoming
    deadlines (tasks + milestones), hours logged vs. budget, and overdue
    tasks -- everything needed for a per-partner dashboard view."""
    partner_email = partner_email.lower()

    projects = (
        db.query(Project)
        .filter(
            Project.engagement_partner_email == partner_email,
            Project.deleted_at.is_(None),
            Project.status.in_(["planning", "active"]),
        )
        .order_by(Project.start_date.is_(None), Project.start_date.asc())
        .all()
    )
    project_ids = [p.id for p in projects]

    now = utcnow()
    horizon = now + timedelta(days=14)

    upcoming_tasks = []
    overdue_tasks = []
    hours_by_project: dict[int, float] = {}

    if project_ids:
        upcoming_tasks = (
            db.query(Task)
            .filter(
                Task.project_id.in_(project_ids),
                Task.deleted_at.is_(None),
                Task.status != "done",
                Task.due_date.isnot(None),
                Task.due_date >= now,
                Task.due_date <= horizon,
            )
            .order_by(Task.due_date.asc())
            .all()
        )
        overdue_tasks = (
            db.query(Task)
            .filter(
                Task.project_id.in_(project_ids),
                Task.deleted_at.is_(None),
                Task.status != "done",
                Task.due_date.isnot(None),
                Task.due_date < now,
            )
            .order_by(Task.due_date.asc())
            .all()
        )

        entries = (
            db.query(TimeEntry)
            .filter(TimeEntry.project_id.in_(project_ids), TimeEntry.deleted_at.is_(None))
            .all()
        )
        for entry in entries:
            hours_by_project[entry.project_id] = hours_by_project.get(entry.project_id, 0.0) + float(entry.hours)

        upcoming_milestones = (
            db.query(Milestone)
            .filter(
                Milestone.project_id.in_(project_ids),
                Milestone.deleted_at.is_(None),
                Milestone.status == "pending",
                Milestone.due_date.isnot(None),
                Milestone.due_date <= horizon,
            )
            .order_by(Milestone.due_date.asc())
            .all()
        )
    else:
        upcoming_milestones = []

    engagements = [
        {
            "id": p.id,
            "name": p.name,
            "client_id": p.client_id,
            "type": p.type,
            "status": p.status,
            "risk_level": p.risk_level,
            "budget": float(p.budget) if p.budget is not None else None,
            "hours_logged": round(hours_by_project.get(p.id, 0.0), 2),
        }
        for p in projects
    ]

    return {
        "partner_email": partner_email,
        "active_engagement_count": len(projects),
        "engagements": engagements,
        "upcoming_deadlines": {
            "tasks": [
                {"id": t.id, "title": t.title, "project_id": t.project_id, "due_date": t.due_date}
                for t in upcoming_tasks
            ],
            "milestones": [
                {"id": m.id, "name": m.name, "project_id": m.project_id, "due_date": m.due_date}
                for m in upcoming_milestones
            ],
        },
        "overdue_tasks": [
            {"id": t.id, "title": t.title, "project_id": t.project_id, "due_date": t.due_date}
            for t in overdue_tasks
        ],
        "overdue_task_count": len(overdue_tasks),
    }


@router.get("/dashboard/client/{client_id}")
def client_dashboard(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Read-layer rollup for a single client: engagements, contacts,
    relationship health, overdue tasks, and contract summary."""
    client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    projects = (
        db.query(Project)
        .filter(Project.client_id == client_id, Project.deleted_at.is_(None))
        .order_by(Project.status.asc(), Project.start_date.is_(None), Project.start_date.asc())
        .all()
    )
    project_ids = [p.id for p in projects]

    contracts = []
    if project_ids:
        contracts = (
            db.query(Contract)
            .filter(Contract.project_id.in_(project_ids), Contract.deleted_at.is_(None))
            .all()
        )

    overdue_tasks = (
        db.query(Task)
        .filter(
            Task.client_id == client_id,
            Task.deleted_at.is_(None),
            Task.status != "done",
            Task.due_date.isnot(None),
            Task.due_date < utcnow(),
        )
        .order_by(Task.due_date.asc())
        .all()
    )

    health = compute_client_health(db, client_id)
    is_override = client.relationship_health is not None

    return {
        "client_id": client_id,
        "client_name": client.display_name,
        "relationship_health": client.relationship_health if is_override else health["computed_health"],
        "computed_health": health["computed_health"],
        "health_reasons": health["reasons"],
        "engagements": [
            {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "status": p.status,
                "budget": float(p.budget) if p.budget is not None else None,
                "engagement_partner_name": p.engagement_partner_name,
            }
            for p in projects
        ],
        "active_engagement_count": sum(1 for p in projects if p.status in ("planning", "active")),
        "contracts": [
            {
                "id": c.id,
                "project_id": c.project_id,
                "name": c.name,
                "billing_type": c.billing_type,
                "value": float(c.value) if c.value is not None else None,
                "status": c.status,
                "expiry_date": c.expiry_date,
            }
            for c in contracts
        ],
        "overdue_tasks": [
            {"id": t.id, "title": t.title, "due_date": t.due_date} for t in overdue_tasks
        ],
        "overdue_task_count": len(overdue_tasks),
    }
