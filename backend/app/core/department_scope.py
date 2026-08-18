"""Department-scoped write permissions, retrofitted onto the existing
client/project/task CRUD surface (and its direct children: contracts,
milestones, change orders, project assignments, client contacts/notes,
and task templates).

Model:
- Reading (GET) stays unrestricted for any authenticated staff member,
  same as before -- this module only gates writes (create/update/delete),
  by being called explicitly from those route handlers.
- An entity with no department linkage (client.department_id is null, or
  a task with no project/client at all) is "unscoped" and stays writable
  by any authenticated staff member, so firms not using departments --
  or firm-wide templates, ad-hoc tasks, etc. -- are unaffected.
- An entity that does belong to a department is writable by: an admin,
  a staff member whose own User.department_id matches it, or that
  department's head (Department.department_head_user_id) -- covering
  both "my team's own work" and "the person appointed to manage this
  department specifically".
- Everyone else gets read-only access to it (enforced simply by GET
  routes never calling require_scoped_write).
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import is_department_manager
from app.models.client import Client
from app.models.contract import Contract
from app.models.project import Project
from app.models.user import User
from app.schemas.user import UserPublic


def get_user_department_id(db: Session, user_id: int) -> int | None:
    user = db.query(User).filter(User.id == user_id).first()
    return user.department_id if user else None


def department_id_for_client(db: Session, client_id: int | None) -> int | None:
    if client_id is None:
        return None
    client = db.query(Client).filter(Client.id == client_id).first()
    return client.department_id if client else None


def department_id_for_project(db: Session, project_id: int | None) -> int | None:
    if project_id is None:
        return None
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    return department_id_for_client(db, project.client_id)


def department_id_for_contract(db: Session, contract_id: int | None) -> int | None:
    if contract_id is None:
        return None
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        return None
    return department_id_for_project(db, contract.project_id)


def department_id_for_task(db: Session, *, project_id: int | None, client_id: int | None) -> int | None:
    """Tasks can be tied to a project, a bare client, or neither (e.g. an
    onboarding checklist item, or a firm-wide to-do) -- resolve whichever
    is present, preferring the project since that's the more specific
    link when both happen to be set."""
    if project_id is not None:
        return department_id_for_project(db, project_id)
    if client_id is not None:
        return department_id_for_client(db, client_id)
    return None


def require_scoped_write(db: Session, current_user: UserPublic, department_id: int | None) -> None:
    """Raises 403 unless the caller may write to an entity in this
    department. department_id=None (unscoped) always passes -- see
    module docstring."""
    if department_id is None:
        return
    if current_user.role == "admin":
        return
    if get_user_department_id(db, current_user.id) == department_id:
        return
    if is_department_manager(db, current_user.id, department_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only manage entities in your own department",
    )
