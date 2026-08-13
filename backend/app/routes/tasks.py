from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, get_user_by_email
from app.core.notify import notify
from app.core.time import utcnow
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.schemas.user import UserPublic

router = APIRouter(prefix="/tasks", tags=["Tasks"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_STATUSES = {"open", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


@router.get("/", response_model=list[TaskOut])
def list_tasks(
    response: Response,
    status: str | None = Query(default=None),
    client_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    assigned_to_me: bool = Query(default=False),
    overdue_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Task).filter(Task.deleted_at.is_(None))

    if status:
        query = query.filter(Task.status == status)

    if client_id is not None:
        query = query.filter(Task.client_id == client_id)

    if project_id is not None:
        query = query.filter(Task.project_id == project_id)

    if assigned_to_me:
        query = query.filter(Task.assigned_to_email == current_user.email)

    if overdue_only:
        query = query.filter(Task.due_date.isnot(None), Task.due_date < utcnow(), Task.status != "done")

    response.headers["X-Total-Count"] = str(query.count())

    return (
        query.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")

    if payload.project_id is not None:
        project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if payload.client_id is not None and payload.client_id != project.client_id:
            raise HTTPException(status_code=400, detail="client_id does not match the project's client")

    assigned_name = None
    if payload.assigned_to_email:
        assignee = get_user_by_email(db, payload.assigned_to_email.lower())
        if not assignee:
            raise HTTPException(status_code=404, detail="Assigned user not found")
        assigned_name = assignee.name

    task = Task(
        title=payload.title,
        description=payload.description,
        client_id=payload.client_id,
        project_id=payload.project_id,
        priority=payload.priority,
        due_date=payload.due_date,
        assigned_to_email=payload.assigned_to_email.lower() if payload.assigned_to_email else None,
        assigned_to_name=assigned_name,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_activity(
        db=db,
        user=current_user,
        action="task_created",
        entity_type="task",
        entity_id=task.id,
        title=f"Task created: {task.title}",
        description=f"Created task '{task.title}'.",
    )

    if task.assigned_to_email and task.assigned_to_email != current_user.email:
        notify(
            db=db,
            user_email=task.assigned_to_email,
            type="task_assigned",
            title=f"New task assigned: {task.title}",
            body=f"{current_user.name} assigned you a task.",
            link=f"/dashboard/tasks?task_id={task.id}",
        )

    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    if "priority" in updates and updates["priority"] not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")

    if "project_id" in updates and updates["project_id"] is not None:
        project = db.query(Project).filter(
            Project.id == updates["project_id"], Project.deleted_at.is_(None)
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    previous_assignee = task.assigned_to_email

    if "assigned_to_email" in updates:
        new_email = updates.pop("assigned_to_email")
        if new_email:
            assignee = get_user_by_email(db, new_email.lower())
            if not assignee:
                raise HTTPException(status_code=404, detail="Assigned user not found")
            task.assigned_to_email = assignee.email
            task.assigned_to_name = assignee.name
        else:
            task.assigned_to_email = None
            task.assigned_to_name = None

    for key, value in updates.items():
        setattr(task, key, value)

    if updates.get("status") == "done" and task.completed_at is None:
        task.completed_at = utcnow()
    elif updates.get("status") is not None and updates.get("status") != "done":
        task.completed_at = None

    db.commit()
    db.refresh(task)

    log_activity(
        db=db,
        user=current_user,
        action="task_updated",
        entity_type="task",
        entity_id=task.id,
        title=f"Task updated: {task.title}",
        description="Task record updated.",
    )

    if (
        task.assigned_to_email
        and task.assigned_to_email != previous_assignee
        and task.assigned_to_email != current_user.email
    ):
        notify(
            db=db,
            user_email=task.assigned_to_email,
            type="task_assigned",
            title=f"Task assigned to you: {task.title}",
            body=f"{current_user.name} assigned you a task.",
            link=f"/dashboard/tasks?task_id={task.id}",
        )

    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="task_deleted",
        entity_type="task",
        entity_id=task_id,
        title=f"Task deleted: {task.title}",
        description="Task removed.",
    )

    return {"message": "Task deleted successfully"}
