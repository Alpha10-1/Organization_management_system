import csv
import io
from datetime import date as date_type, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.billing import compute_realization, money
from app.core.client_health import compute_client_health
from app.core.deps import get_current_active_user
from app.core.time import utcnow
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.client import Client
from app.models.contract import Contract
from app.models.department import Department
from app.models.file_record import FileRecord
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.models.task import Task
from app.models.time_entry import TimeEntry
from app.models.user import User
from app.schemas.invoice import RealizationReportOut
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


@router.get("/dashboard/compliance")
def compliance_dashboard(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Firm-wide risk/compliance rollup: every open (non-completed,
    non-cancelled) engagement flagged high/medium risk or carrying a
    compliance flag, plus the most recent risk/compliance-relevant
    activity across all engagements. This is the read-layer partners or a
    risk committee would use to see exposure across the whole firm at a
    glance, rather than one engagement or one partner at a time."""
    open_statuses = ("planning", "active", "on_hold")

    flagged_projects = (
        db.query(Project)
        .filter(
            Project.deleted_at.is_(None),
            Project.status.in_(open_statuses),
            (Project.risk_level.in_(["high", "medium"])) | (Project.compliance_flag.isnot(None)),
        )
        .order_by(
            case((Project.risk_level == "high", 0), (Project.risk_level == "medium", 1), else_=2),
            Project.name.asc(),
        )
        .all()
    )
    project_ids = [p.id for p in flagged_projects]

    overdue_by_project: dict[int, int] = {}
    if project_ids:
        overdue_rows = (
            db.query(Task.project_id, func.count(Task.id))
            .filter(
                Task.project_id.in_(project_ids),
                Task.deleted_at.is_(None),
                Task.status != "done",
                Task.due_date.isnot(None),
                Task.due_date < utcnow(),
            )
            .group_by(Task.project_id)
            .all()
        )
        overdue_by_project = dict(overdue_rows)

    recent_changes = (
        db.query(ActivityLog)
        .filter(ActivityLog.entity_type == "project", ActivityLog.action == "project_risk_changed")
        .order_by(ActivityLog.created_at.desc())
        .limit(25)
        .all()
    )

    return {
        "generated_at": utcnow(),
        "high_risk_count": sum(1 for p in flagged_projects if p.risk_level == "high"),
        "medium_risk_count": sum(1 for p in flagged_projects if p.risk_level == "medium"),
        "compliance_flagged_count": sum(1 for p in flagged_projects if p.compliance_flag),
        "engagements": [
            {
                "id": p.id,
                "name": p.name,
                "client_id": p.client_id,
                "type": p.type,
                "status": p.status,
                "risk_level": p.risk_level,
                "compliance_flag": p.compliance_flag,
                "engagement_partner_name": p.engagement_partner_name,
                "overdue_task_count": overdue_by_project.get(p.id, 0),
            }
            for p in flagged_projects
        ],
        "recent_risk_changes": [
            {
                "project_id": log.entity_id,
                "title": log.title,
                "description": log.description,
                "user_name": log.user_name,
                "created_at": log.created_at,
            }
            for log in recent_changes
        ],
    }


@router.get("/dashboard/capacity")
def capacity_dashboard(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Firm-wide staffing capacity: for every active staff member, how
    much of their time is committed across open engagements right now.
    Only individual (user_id) assignments carry an allocation_percent --
    department-wide assignments staff the whole team without a per-person
    split, so they're surfaced separately rather than folded into the
    percentage math."""
    open_statuses = ("planning", "active", "on_hold")

    users = db.query(User).filter(User.disabled.is_(False)).order_by(User.name).all()

    assignments = (
        db.query(ProjectAssignment, Project)
        .join(Project, ProjectAssignment.project_id == Project.id)
        .filter(
            ProjectAssignment.user_id.isnot(None),
            Project.deleted_at.is_(None),
            Project.status.in_(open_statuses),
        )
        .all()
    )

    by_user: dict[int, list[dict]] = {}
    for assignment, project in assignments:
        by_user.setdefault(assignment.user_id, []).append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "role": assignment.role,
                "allocation_percent": assignment.allocation_percent,
            }
        )

    people = []
    for user in users:
        engagements = by_user.get(user.id, [])
        total_allocated = sum(e["allocation_percent"] or 0 for e in engagements)
        unspecified_count = sum(1 for e in engagements if e["allocation_percent"] is None)

        if not engagements:
            status_label = "bench"
        elif total_allocated > 100:
            status_label = "over_allocated"
        elif total_allocated < 50:
            status_label = "under_allocated"
        else:
            status_label = "fully_allocated"

        people.append(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "position": user.position,
                "department_id": user.department_id,
                "total_allocated_percent": total_allocated,
                "unspecified_allocation_count": unspecified_count,
                "status": status_label,
                "engagements": engagements,
            }
        )

    return {
        "generated_at": utcnow(),
        "over_allocated_count": sum(1 for p in people if p["status"] == "over_allocated"),
        "under_allocated_count": sum(1 for p in people if p["status"] == "under_allocated"),
        "bench_count": sum(1 for p in people if p["status"] == "bench"),
        "people": people,
    }


@router.get("/realization", response_model=RealizationReportOut)
def realization_report(
    group_by: str = Query(default="project", pattern="^(project|partner|department)$"),
    project_id: int | None = Query(default=None),
    start_date: date_type | None = Query(default=None),
    end_date: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Realization rate = billed value / worked value over the period,
    rolled up by engagement, partner, or department. This is the
    headline "are we actually capturing the revenue our people are
    generating" number -- a rate well under 100% means work is being done
    that never turns into an invoice.
    """
    department_by_project = None
    if group_by == "department":
        rows = (
            db.query(Project.id, Client.department_id, Department.name)
            .join(Client, Project.client_id == Client.id)
            .outerjoin(Department, Client.department_id == Department.id)
            .all()
        )
        department_by_project = {
            project_id_: ((dept_id, dept_name) if dept_id is not None else None)
            for project_id_, dept_id, dept_name in rows
        }

    result_rows = compute_realization(
        db,
        group_by=group_by,
        start_date=start_date,
        end_date=end_date,
        project_id=project_id,
        department_by_project=department_by_project,
    )

    firm_worked = sum((r.worked_value for r in result_rows), Decimal("0.00"))
    firm_billed = sum((r.billed_value for r in result_rows), Decimal("0.00"))

    return {
        "group_by": group_by,
        "start_date": start_date,
        "end_date": end_date,
        "firm_worked_value": firm_worked,
        "firm_billed_value": firm_billed,
        "firm_realization_rate": (firm_billed / firm_worked).quantize(Decimal("0.0001")) if firm_worked else None,
        "rows": [
            {
                "key": r.key,
                "label": r.label,
                "worked_hours": r.worked_hours,
                "worked_value": r.worked_value,
                "billed_value": r.billed_value,
                "realization_rate": r.realization_rate,
            }
            for r in result_rows
        ],
    }
