from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user, get_user_by_email
from app.core.notify import notify
from app.core.time import utcnow
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.schemas.task import TaskCreate, TaskDetail, TaskOut, TaskUpdate
from app.schemas.task_dependency import TaskDependencyCreate, TaskDependencyOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/tasks", tags=["Tasks"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_STATUSES = {"open", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}
RECURRENCE_STEPS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


def _spawn_next_occurrence(db: Session, task: Task, current_user: UserPublic) -> Task | None:
    """When a recurring task is completed, clone the next occurrence with
    its due date rolled forward by the recurrence interval. Stops once
    recurrence_end_date has passed."""
    if not task.recurrence_rule or not task.due_date:
        return None

    step = RECURRENCE_STEPS.get(task.recurrence_rule)
    if step is None:
        return None

    next_due = task.due_date + step
    if task.recurrence_end_date and next_due > task.recurrence_end_date:
        return None

    series_root_id = task.recurrence_parent_id or task.id

    clone = Task(
        title=task.title,
        description=task.description,
        client_id=task.client_id,
        project_id=task.project_id,
        priority=task.priority,
        due_date=next_due,
        assigned_to_email=task.assigned_to_email,
        assigned_to_name=task.assigned_to_name,
        recurrence_rule=task.recurrence_rule,
        recurrence_end_date=task.recurrence_end_date,
        recurrence_parent_id=series_root_id,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(clone)
    return clone


def _dependency_ids(db: Session, task_id: int) -> tuple[list[int], list[int]]:
    blocked_by = [
        row[0]
        for row in db.query(TaskDependency.depends_on_task_id).filter(TaskDependency.task_id == task_id).all()
    ]
    blocks = [
        row[0]
        for row in db.query(TaskDependency.task_id).filter(TaskDependency.depends_on_task_id == task_id).all()
    ]
    return blocked_by, blocks


def _has_cycle(db: Session, task_id: int, depends_on_task_id: int) -> bool:
    """True if adding task_id -> depends_on_task_id would create a cycle,
    i.e. depends_on_task_id (transitively) already depends on task_id."""
    seen = set()
    frontier = [depends_on_task_id]
    while frontier:
        current = frontier.pop()
        if current == task_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(
            row[0]
            for row in db.query(TaskDependency.depends_on_task_id)
            .filter(TaskDependency.task_id == current)
            .all()
        )
    return False


@router.get("/", response_model=list[TaskOut])
def list_tasks(
    response: Response,
    status: str | None = Query(default=None),
    client_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    parent_task_id: int | None = Query(default=None),
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

    if parent_task_id is not None:
        query = query.filter(Task.parent_task_id == parent_task_id)

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

    if payload.parent_task_id is not None:
        parent = db.query(Task).filter(Task.id == payload.parent_task_id, Task.deleted_at.is_(None)).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent task not found")

    if payload.recurrence_rule and not payload.due_date:
        raise HTTPException(status_code=400, detail="A due_date is required to set up a recurring task")

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
        parent_task_id=payload.parent_task_id,
        priority=payload.priority,
        due_date=payload.due_date,
        assigned_to_email=payload.assigned_to_email.lower() if payload.assigned_to_email else None,
        assigned_to_name=assigned_name,
        recurrence_rule=payload.recurrence_rule,
        recurrence_end_date=payload.recurrence_end_date,
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


@router.get("/{task_id}/detail", response_model=TaskDetail)
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    subtasks = db.query(Task).filter(Task.parent_task_id == task_id, Task.deleted_at.is_(None)).all()
    blocked_by, blocks = _dependency_ids(db, task_id)

    is_blocked = False
    if blocked_by:
        open_blockers = (
            db.query(Task)
            .filter(Task.id.in_(blocked_by), Task.deleted_at.is_(None), Task.status != "done")
            .count()
        )
        is_blocked = open_blockers > 0

    detail = TaskDetail.model_validate(task)
    detail.subtask_count = len(subtasks)
    detail.open_subtask_count = sum(1 for s in subtasks if s.status != "done")
    detail.blocked_by = blocked_by
    detail.blocks = blocks
    detail.is_blocked = is_blocked
    return detail


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

    if "parent_task_id" in updates and updates["parent_task_id"] is not None:
        if updates["parent_task_id"] == task_id:
            raise HTTPException(status_code=400, detail="A task cannot be its own parent")
        parent = db.query(Task).filter(Task.id == updates["parent_task_id"], Task.deleted_at.is_(None)).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent task not found")

    if updates.get("status") == "done":
        blocked_by, _ = _dependency_ids(db, task_id)
        if blocked_by:
            open_blockers = (
                db.query(Task)
                .filter(Task.id.in_(blocked_by), Task.deleted_at.is_(None), Task.status != "done")
                .count()
            )
            if open_blockers:
                raise HTTPException(
                    status_code=400,
                    detail="This task is blocked by other incomplete tasks and cannot be marked done",
                )

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

    spawned = None
    if updates.get("status") == "done" and task.completed_at is None:
        task.completed_at = utcnow()
        spawned = _spawn_next_occurrence(db, task, current_user)
    elif updates.get("status") is not None and updates.get("status") != "done":
        task.completed_at = None

    db.commit()
    db.refresh(task)
    if spawned:
        db.refresh(spawned)

    log_activity(
        db=db,
        user=current_user,
        action="task_updated",
        entity_type="task",
        entity_id=task.id,
        title=f"Task updated: {task.title}",
        description="Task record updated.",
    )

    if spawned:
        log_activity(
            db=db,
            user=current_user,
            action="task_created",
            entity_type="task",
            entity_id=spawned.id,
            title=f"Recurring task generated: {spawned.title}",
            description=f"Next occurrence of '{spawned.title}' created for {spawned.due_date}.",
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


# --- Dependencies ---------------------------------------------------------


@router.get("/{task_id}/dependencies", response_model=list[TaskDependencyOut])
def list_task_dependencies(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return db.query(TaskDependency).filter(TaskDependency.task_id == task_id).all()


@router.post("/{task_id}/dependencies", response_model=TaskDependencyOut)
def add_task_dependency(
    task_id: int,
    payload: TaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if task_id == payload.depends_on_task_id:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself")

    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    blocker = db.query(Task).filter(Task.id == payload.depends_on_task_id, Task.deleted_at.is_(None)).first()
    if not blocker:
        raise HTTPException(status_code=404, detail="Dependency task not found")

    existing = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id == task_id, TaskDependency.depends_on_task_id == payload.depends_on_task_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This dependency already exists")

    if _has_cycle(db, task_id, payload.depends_on_task_id):
        raise HTTPException(status_code=400, detail="This dependency would create a circular reference")

    dependency = TaskDependency(task_id=task_id, depends_on_task_id=payload.depends_on_task_id)
    db.add(dependency)
    db.commit()
    db.refresh(dependency)

    log_activity(
        db=db,
        user=current_user,
        action="task_dependency_added",
        entity_type="task",
        entity_id=task_id,
        title=f"Dependency added: {task.title}",
        description=f"'{task.title}' now depends on '{blocker.title}'.",
    )

    return dependency


@router.delete("/{task_id}/dependencies/{dependency_id}")
def delete_task_dependency(
    task_id: int,
    dependency_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    dependency = (
        db.query(TaskDependency)
        .filter(TaskDependency.id == dependency_id, TaskDependency.task_id == task_id)
        .first()
    )
    if not dependency:
        raise HTTPException(status_code=404, detail="Dependency not found")

    db.delete(dependency)
    db.commit()
    return {"message": "Dependency removed successfully"}
