from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, get_user_by_email
from app.core.time import utcnow
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.client import Client
from app.models.department import Department
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.models.task import Task
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectSummary, ProjectUpdate
from app.schemas.project_assignment import (
    ProjectAssignmentCreate,
    ProjectAssignmentOut,
    ProjectAssignmentUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/projects", tags=["Projects"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_TYPES = {"audit", "tax", "advisory", "systems_implementation", "other"}
VALID_STATUSES = {"planning", "active", "on_hold", "completed", "cancelled"}
VALID_RISK_LEVELS = {"low", "medium", "high"}


def _resolve_partner_manager(db: Session, payload) -> dict:
    """Look up display names for the partner/manager emails, mirroring how
    tasks resolve assigned_to_name from assigned_to_email."""
    extra = {}
    if payload.engagement_partner_email:
        partner = get_user_by_email(db, payload.engagement_partner_email.lower())
        if not partner:
            raise HTTPException(status_code=404, detail="Engagement partner not found")
        extra["engagement_partner_email"] = partner.email
        extra["engagement_partner_name"] = partner.name
    if payload.engagement_manager_email:
        manager = get_user_by_email(db, payload.engagement_manager_email.lower())
        if not manager:
            raise HTTPException(status_code=404, detail="Engagement manager not found")
        extra["engagement_manager_email"] = manager.email
        extra["engagement_manager_name"] = manager.name
    return extra


def _with_task_rollups(db: Session, projects: list[Project]) -> list[ProjectSummary]:
    if not projects:
        return []
    project_ids = [p.id for p in projects]

    counts = (
        db.query(
            Task.project_id,
            func.count(Task.id).label("total"),
            func.sum(case((Task.status != "done", 1), else_=0)).label("open"),
        )
        .filter(Task.project_id.in_(project_ids), Task.deleted_at.is_(None))
        .group_by(Task.project_id)
        .all()
    )
    # Overdue is easier as a separate simple query than shoehorning into the
    # cross-database CASE/CAST above.
    overdue_counts = dict(
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
    totals = {row[0]: (row[1] or 0, row[2] or 0) for row in counts}

    results = []
    for p in projects:
        total, open_count = totals.get(p.id, (0, 0))
        summary = ProjectSummary.model_validate(p)
        summary.task_count = total
        summary.open_task_count = open_count
        summary.overdue_task_count = overdue_counts.get(p.id, 0)
        results.append(summary)
    return results


@router.get("/", response_model=list[ProjectSummary])
def list_projects(
    response: Response,
    client_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    engagement_partner_email: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Project).filter(Project.deleted_at.is_(None))

    if client_id is not None:
        query = query.filter(Project.client_id == client_id)
    if status:
        query = query.filter(Project.status == status)
    if type:
        query = query.filter(Project.type == type)
    if risk_level:
        query = query.filter(Project.risk_level == risk_level)
    if engagement_partner_email:
        query = query.filter(Project.engagement_partner_email == engagement_partner_email.lower())

    response.headers["X-Total-Count"] = str(query.count())

    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    return _with_task_rollups(db, projects)


@router.post("/", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {sorted(VALID_TYPES)}")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
    if payload.risk_level not in VALID_RISK_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid risk_level. Must be one of: {sorted(VALID_RISK_LEVELS)}")

    client = db.query(Client).filter(Client.id == payload.client_id, Client.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    extra = _resolve_partner_manager(db, payload)

    project = Project(
        client_id=payload.client_id,
        name=payload.name,
        type=payload.type,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        description=payload.description,
        risk_level=payload.risk_level,
        compliance_flag=payload.compliance_flag,
        objectives=payload.objectives,
        deliverables=payload.deliverables,
        stakeholders=payload.stakeholders,
        billing_notes=payload.billing_notes,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
        **extra,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    log_activity(
        db=db,
        user=current_user,
        action="project_created",
        entity_type="project",
        entity_id=project.id,
        title=f"Engagement created: {project.name}",
        description=f"Created engagement '{project.name}' for client #{project.client_id}.",
    )

    return project


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _with_task_rollups(db, [project])[0]


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updates = payload.model_dump(exclude_unset=True)

    if "type" in updates and updates["type"] not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {sorted(VALID_TYPES)}")
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
    if "risk_level" in updates and updates["risk_level"] not in VALID_RISK_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid risk_level. Must be one of: {sorted(VALID_RISK_LEVELS)}")

    if "client_id" in updates:
        client = db.query(Client).filter(Client.id == updates["client_id"], Client.deleted_at.is_(None)).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    new_start = updates.get("start_date", project.start_date)
    new_end = updates.get("end_date", project.end_date)
    if new_start and new_end and new_end < new_start:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    previous_status = project.status
    previous_risk_level = project.risk_level
    previous_compliance_flag = project.compliance_flag

    if "engagement_partner_email" in updates:
        email = updates.pop("engagement_partner_email")
        if email:
            partner = get_user_by_email(db, email.lower())
            if not partner:
                raise HTTPException(status_code=404, detail="Engagement partner not found")
            project.engagement_partner_email = partner.email
            project.engagement_partner_name = partner.name
        else:
            project.engagement_partner_email = None
            project.engagement_partner_name = None

    if "engagement_manager_email" in updates:
        email = updates.pop("engagement_manager_email")
        if email:
            manager = get_user_by_email(db, email.lower())
            if not manager:
                raise HTTPException(status_code=404, detail="Engagement manager not found")
            project.engagement_manager_email = manager.email
            project.engagement_manager_name = manager.name
        else:
            project.engagement_manager_email = None
            project.engagement_manager_name = None

    for key, value in updates.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    status_changed = "status" in updates and updates["status"] != previous_status
    risk_changed = "risk_level" in updates and updates["risk_level"] != previous_risk_level
    compliance_changed = (
        "compliance_flag" in updates and updates["compliance_flag"] != previous_compliance_flag
    )

    change_notes = []
    if status_changed:
        change_notes.append(f"Status changed from '{previous_status}' to '{project.status}'.")
    if risk_changed:
        change_notes.append(f"Risk level changed from '{previous_risk_level}' to '{project.risk_level}'.")
    if compliance_changed:
        change_notes.append(
            f"Compliance flag changed from '{previous_compliance_flag or 'none'}' "
            f"to '{project.compliance_flag or 'none'}'."
        )

    log_activity(
        db=db,
        user=current_user,
        action="project_updated",
        entity_type="project",
        entity_id=project.id,
        title=f"Engagement updated: {project.name}",
        description=" ".join(change_notes) if change_notes else "Engagement record updated.",
    )

    # Risk/compliance changes are logged as a second, distinctly-actioned
    # entry so a compliance audit trail can be queried without having to
    # parse free-text descriptions of general "project_updated" events.
    if risk_changed or compliance_changed:
        log_activity(
            db=db,
            user=current_user,
            action="project_risk_changed",
            entity_type="project",
            entity_id=project.id,
            title=f"Risk/compliance updated: {project.name}",
            description=" ".join(
                note for note in [
                    f"Risk level changed from '{previous_risk_level}' to '{project.risk_level}'."
                    if risk_changed else None,
                    f"Compliance flag changed from '{previous_compliance_flag or 'none'}' "
                    f"to '{project.compliance_flag or 'none'}'."
                    if compliance_changed else None,
                ]
                if note
            ),
        )

    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="project_deleted",
        entity_type="project",
        entity_id=project_id,
        title=f"Engagement deleted: {project.name}",
        description="Engagement removed (soft delete). Tasks remain but are unlinked in list views.",
    )

    return {"message": "Project deleted successfully"}


@router.get("/{project_id}/history")
def get_project_history(
    project_id: int,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Lightweight audit trail for an engagement: every logged status,
    risk-level and compliance-flag change, newest first. Reuses the
    existing ActivityLog table rather than a separate audit model -- an
    engagement's history is just its activity log filtered to itself."""
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.entity_type == "project", ActivityLog.entity_id == project_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "action": log.action,
            "title": log.title,
            "description": log.description,
            "user_name": log.user_name,
            "user_email": log.user_email,
            "created_at": log.created_at,
        }
        for log in logs
    ]


# --- Team assignment (individuals or whole departments) -------------------


def _assignment_out(db: Session, assignment: ProjectAssignment) -> ProjectAssignmentOut:
    user_name = None
    department_name = None
    if assignment.user_id:
        user = db.query(User).filter(User.id == assignment.user_id).first()
        user_name = user.name if user else None
    if assignment.department_id:
        dept = db.query(Department).filter(Department.id == assignment.department_id).first()
        department_name = dept.name if dept else None

    return ProjectAssignmentOut(
        id=assignment.id,
        project_id=assignment.project_id,
        user_id=assignment.user_id,
        department_id=assignment.department_id,
        user_name=user_name,
        department_name=department_name,
        role=assignment.role,
        allocation_percent=assignment.allocation_percent,
        assigned_by_email=assignment.assigned_by_email,
        assigned_by_name=assignment.assigned_by_name,
        created_at=assignment.created_at,
    )


@router.get("/{project_id}/assignments", response_model=list[ProjectAssignmentOut])
def list_project_assignments(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignments = (
        db.query(ProjectAssignment)
        .filter(ProjectAssignment.project_id == project_id)
        .order_by(ProjectAssignment.created_at.asc())
        .all()
    )
    return [_assignment_out(db, a) for a in assignments]


@router.post("/{project_id}/assignments", response_model=ProjectAssignmentOut)
def add_project_assignment(
    project_id: int,
    payload: ProjectAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.user_id:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        existing = (
            db.query(ProjectAssignment)
            .filter(ProjectAssignment.project_id == project_id, ProjectAssignment.user_id == payload.user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="This user is already assigned to the engagement")
    else:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        existing = (
            db.query(ProjectAssignment)
            .filter(ProjectAssignment.project_id == project_id, ProjectAssignment.department_id == payload.department_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="This department is already assigned to the engagement")

    assignment = ProjectAssignment(
        project_id=project_id,
        user_id=payload.user_id,
        department_id=payload.department_id,
        role=payload.role,
        allocation_percent=payload.allocation_percent,
        assigned_by_email=current_user.email,
        assigned_by_name=current_user.name,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    target = f"user #{payload.user_id}" if payload.user_id else f"department #{payload.department_id}"
    log_activity(
        db=db,
        user=current_user,
        action="project_assignment_added",
        entity_type="project",
        entity_id=project_id,
        title=f"Team assigned: {project.name}",
        description=f"Assigned {target} to engagement '{project.name}'" + (f" as {payload.role}." if payload.role else "."),
    )

    return _assignment_out(db, assignment)


@router.put("/{project_id}/assignments/{assignment_id}", response_model=ProjectAssignmentOut)
def update_project_assignment(
    project_id: int,
    assignment_id: int,
    payload: ProjectAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    assignment = (
        db.query(ProjectAssignment)
        .filter(ProjectAssignment.id == assignment_id, ProjectAssignment.project_id == project_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    updates = payload.model_dump(exclude_unset=True)
    if "allocation_percent" in updates and updates["allocation_percent"] is not None and not assignment.user_id:
        raise HTTPException(
            status_code=400,
            detail="allocation_percent only applies to individual (user_id) assignments",
        )

    for key, value in updates.items():
        setattr(assignment, key, value)

    db.commit()
    db.refresh(assignment)
    return _assignment_out(db, assignment)


@router.delete("/{project_id}/assignments/{assignment_id}")
def remove_project_assignment(
    project_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    assignment = (
        db.query(ProjectAssignment)
        .filter(ProjectAssignment.id == assignment_id, ProjectAssignment.project_id == project_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": "Assignment removed successfully"}
