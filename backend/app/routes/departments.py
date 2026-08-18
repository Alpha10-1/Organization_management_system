from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, require_department_manage, require_role
from app.db.session import get_db
from app.models.client import Client
from app.models.contract import Contract
from app.models.department import Department
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentDashboard, DepartmentOut, DepartmentUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/departments", tags=["Departments"])


def _validate_department_head(db: Session, department_head_user_id: int | None) -> None:
    if department_head_user_id is None:
        return
    head = db.query(User).filter(User.id == department_head_user_id).first()
    if not head:
        raise HTTPException(status_code=400, detail="Department head not found")


@router.get("/", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return db.query(Department).order_by(Department.name).all()


@router.get("/{department_id}")
def get_department_detail(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Department detail with its head and staff, staff grouped by
    position so the read layer for 'who's in this department, and how
    senior are they' is a single call rather than several."""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    members = (
        db.query(User)
        .filter(User.department_id == department_id)
        .order_by(User.name)
        .all()
    )
    head = None
    if department.department_head_user_id:
        head = db.query(User).filter(User.id == department.department_head_user_id).first()

    by_position: dict[str, list[dict]] = {}
    for m in members:
        by_position.setdefault(m.position or "unassigned", []).append(
            {"id": m.id, "name": m.name, "email": m.email, "manager_id": m.manager_id}
        )

    return {
        "id": department.id,
        "name": department.name,
        "description": department.description,
        "department_head": (
            {"id": head.id, "name": head.name, "email": head.email} if head else None
        ),
        "staff_count": len(members),
        "staff_by_position": by_position,
    }


@router.post("/", response_model=DepartmentOut)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    if db.query(Department).filter(Department.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A department with this name already exists")

    _validate_department_head(db, payload.department_head_user_id)

    department = Department(
        name=payload.name,
        description=payload.description,
        department_head_user_id=payload.department_head_user_id,
        annual_budget=payload.annual_budget,
        cost_center_code=payload.cost_center_code,
    )
    db.add(department)
    db.commit()
    db.refresh(department)

    log_activity(
        db=db,
        user=current_user,
        action="department_created",
        entity_type="department",
        entity_id=department.id,
        title=f"Department created: {department.name}",
        description=f"Created department '{department.name}'.",
    )

    return department


@router.put("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Full edit rights: admin, or the department's own head (e.g. to keep
    their cost center code or annual budget current) -- see
    core.deps.require_department_manage for the scope of this check."""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    require_department_manage(db, current_user, department_id)

    updates = payload.model_dump(exclude_unset=True)
    if "department_head_user_id" in updates:
        _validate_department_head(db, updates["department_head_user_id"])

    for key, value in updates.items():
        setattr(department, key, value)

    db.commit()
    db.refresh(department)

    log_activity(
        db=db,
        user=current_user,
        action="department_updated",
        entity_type="department",
        entity_id=department.id,
        title=f"Department updated: {department.name}",
        description="Department record updated.",
    )

    return department


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    db.delete(department)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="department_deleted",
        entity_type="department",
        entity_id=department_id,
        title=f"Department deleted: {department.name}",
        description="Department removed. Clients/users in it are unassigned, not deleted.",
    )

    return {"message": "Department deleted successfully"}


@router.get("/{department_id}/dashboard", response_model=DepartmentDashboard)
def department_dashboard(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Department-level KPI read layer: utilization, active engagement
    count, average risk level, and revenue -- the same pattern as the
    firm-wide capacity dashboard (reports.py), scoped to one department.
    Engagements are attributed to a department via their client's
    department_id, since projects don't carry one directly."""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    staff = db.query(User).filter(User.department_id == department_id, User.disabled.is_(False)).all()
    staff_ids = [u.id for u in staff]

    open_statuses = ("planning", "active", "on_hold")

    allocated_by_user: dict[int, int] = {}
    if staff_ids:
        assignments = (
            db.query(ProjectAssignment, Project)
            .join(Project, ProjectAssignment.project_id == Project.id)
            .filter(
                ProjectAssignment.user_id.in_(staff_ids),
                Project.deleted_at.is_(None),
                Project.status.in_(open_statuses),
            )
            .all()
        )
        for assignment, _project in assignments:
            allocated_by_user[assignment.user_id] = allocated_by_user.get(assignment.user_id, 0) + (
                assignment.allocation_percent or 0
            )

    over_allocated = under_allocated = bench = 0
    total_allocated_percent = 0
    for user in staff:
        allocated = allocated_by_user.get(user.id, 0)
        total_allocated_percent += allocated
        if allocated == 0:
            bench += 1
        elif allocated > 100:
            over_allocated += 1
        elif allocated < 50:
            under_allocated += 1
    average_allocated_percent = (total_allocated_percent / len(staff)) if staff else 0.0

    engagements = (
        db.query(Project)
        .join(Client, Project.client_id == Client.id)
        .filter(
            Client.department_id == department_id,
            Project.deleted_at.is_(None),
            Project.status.in_(open_statuses),
        )
        .all()
    )

    average_risk_level = None
    if engagements:
        risk_scores = {"low": 1, "medium": 2, "high": 3}
        avg_score = sum(risk_scores.get(p.risk_level, 1) for p in engagements) / len(engagements)
        average_risk_level = min(risk_scores, key=lambda level: abs(risk_scores[level] - avg_score))

    revenue_to_date = Decimal("0")
    if engagements:
        project_ids = [p.id for p in engagements]
        signed_contracts = (
            db.query(Contract)
            .filter(
                Contract.project_id.in_(project_ids),
                Contract.deleted_at.is_(None),
                Contract.status == "signed",
                Contract.value.isnot(None),
            )
            .all()
        )
        revenue_to_date = sum((c.value for c in signed_contracts), Decimal("0"))

    budget_variance = revenue_to_date - department.annual_budget if department.annual_budget is not None else None

    return DepartmentDashboard(
        department_id=department.id,
        department_name=department.name,
        cost_center_code=department.cost_center_code,
        annual_budget=department.annual_budget,
        staff_count=len(staff),
        average_allocated_percent=round(average_allocated_percent, 1),
        over_allocated_count=over_allocated,
        under_allocated_count=under_allocated,
        bench_count=bench,
        active_engagement_count=len(engagements),
        average_risk_level=average_risk_level,
        revenue_to_date=revenue_to_date,
        budget_variance=budget_variance,
    )
