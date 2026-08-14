from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.time import utcnow
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.task_template import TaskTemplate, TaskTemplateItem
from app.schemas.task import TaskOut
from app.schemas.task_template import (
    TaskTemplateApplyRequest,
    TaskTemplateCreate,
    TaskTemplateOut,
    TaskTemplateUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/task-templates", tags=["Task Templates"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200


@router.get("/", response_model=list[TaskTemplateOut])
def list_task_templates(
    response: Response,
    engagement_type: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(TaskTemplate).filter(TaskTemplate.deleted_at.is_(None))

    if engagement_type:
        query = query.filter(TaskTemplate.engagement_type == engagement_type)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(TaskTemplate.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=TaskTemplateOut)
def create_task_template(
    payload: TaskTemplateCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    template = TaskTemplate(
        name=payload.name,
        engagement_type=payload.engagement_type,
        description=payload.description,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(template)
    db.flush()  # assign template.id before creating items

    for index, item in enumerate(payload.items):
        db.add(
            TaskTemplateItem(
                template_id=template.id,
                title=item.title,
                description=item.description,
                priority=item.priority,
                relative_due_days=item.relative_due_days,
                order_index=item.order_index or index,
            )
        )

    db.commit()
    db.refresh(template)

    log_activity(
        db=db,
        user=current_user,
        action="task_template_created",
        entity_type="task_template",
        entity_id=template.id,
        title=f"Task template created: {template.name}",
        description=f"Created template '{template.name}' with {len(payload.items)} item(s).",
    )

    return template


@router.get("/{template_id}", response_model=TaskTemplateOut)
def get_task_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id, TaskTemplate.deleted_at.is_(None)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")
    return template


@router.put("/{template_id}", response_model=TaskTemplateOut)
def update_task_template(
    template_id: int,
    payload: TaskTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id, TaskTemplate.deleted_at.is_(None)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_task_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id, TaskTemplate.deleted_at.is_(None)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")

    template.deleted_at = utcnow()
    db.commit()
    return {"message": "Task template deleted successfully"}


@router.post("/{template_id}/apply", response_model=list[TaskOut])
def apply_task_template(
    template_id: int,
    payload: TaskTemplateApplyRequest,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Clone every item on a template onto a project as real tasks. Due
    dates are computed as anchor_date + relative_due_days (anchor_date
    defaults to the project's start_date, or today if neither is set)."""
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id, TaskTemplate.deleted_at.is_(None)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")

    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    anchor = payload.anchor_date or project.start_date or utcnow()

    items = (
        db.query(TaskTemplateItem)
        .filter(TaskTemplateItem.template_id == template_id)
        .order_by(TaskTemplateItem.order_index.asc())
        .all()
    )
    if not items:
        raise HTTPException(status_code=400, detail="Template has no items to apply")

    created_tasks = []
    for item in items:
        due_date = anchor + timedelta(days=item.relative_due_days) if item.relative_due_days is not None else None
        task = Task(
            title=item.title,
            description=item.description,
            client_id=project.client_id,
            project_id=project.id,
            priority=item.priority,
            due_date=due_date,
            created_by_email=current_user.email,
            created_by_name=current_user.name,
        )
        db.add(task)
        created_tasks.append(task)

    db.commit()
    for task in created_tasks:
        db.refresh(task)

    log_activity(
        db=db,
        user=current_user,
        action="task_template_applied",
        entity_type="project",
        entity_id=project.id,
        title=f"Template applied: {template.name}",
        description=f"Cloned {len(created_tasks)} task(s) from template '{template.name}' onto engagement '{project.name}'.",
    )

    return created_tasks
