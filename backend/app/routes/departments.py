from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, require_role
from app.db.session import get_db
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    return db.query(Department).order_by(Department.name).all()


@router.post("/", response_model=DepartmentOut)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(require_role("admin")),
):
    if db.query(Department).filter(Department.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A department with this name already exists")

    department = Department(name=payload.name, description=payload.description)
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
    current_user: UserPublic = Depends(require_role("admin")),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(department, key, value)

    db.commit()
    db.refresh(department)
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
