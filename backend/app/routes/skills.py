from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.deps import get_current_active_user
from app.core.time import utcnow
from app.db.session import get_db
from app.models.staff_skill import StaffSkill
from app.models.user import User
from app.schemas.staff_skill import (
    StaffSkillCreate,
    StaffSkillMatrixEntry,
    StaffSkillOut,
    StaffSkillUpdate,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/skills", tags=["Skills & Certifications"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_CATEGORIES = {"skill", "certification"}
VALID_PROFICIENCY_LEVELS = {"beginner", "intermediate", "advanced", "expert"}


@router.get("/", response_model=list[StaffSkillOut])
def list_skills(
    response: Response,
    user_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    name: str | None = Query(default=None),
    expiring_within_days: int | None = Query(default=None, ge=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(StaffSkill).filter(StaffSkill.deleted_at.is_(None))

    if user_id is not None:
        query = query.filter(StaffSkill.user_id == user_id)
    if category:
        query = query.filter(StaffSkill.category == category)
    if name:
        query = query.filter(StaffSkill.name.ilike(f"%{name}%"))
    if expiring_within_days is not None:
        cutoff = utcnow().date() + timedelta(days=expiring_within_days)
        query = query.filter(StaffSkill.expiry_date.isnot(None), StaffSkill.expiry_date <= cutoff)

    response.headers["X-Total-Count"] = str(query.count())

    return query.order_by(StaffSkill.name.asc()).offset(skip).limit(limit).all()


@router.get("/matrix", response_model=list[StaffSkillMatrixEntry])
def skills_matrix(
    department_id: int | None = Query(default=None),
    name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Who can I put on this audit: every active staff member (optionally
    scoped to a department) with the skills/certifications they hold,
    optionally filtered to a specific skill name so staffing decisions are
    data-driven instead of tribal knowledge."""
    user_query = db.query(User).filter(User.disabled.is_(False))
    if department_id is not None:
        user_query = user_query.filter(User.department_id == department_id)
    users = user_query.order_by(User.name).all()
    user_ids = [u.id for u in users]

    skills_by_user: dict[int, list[StaffSkill]] = {}
    if user_ids:
        skill_query = db.query(StaffSkill).filter(
            StaffSkill.user_id.in_(user_ids), StaffSkill.deleted_at.is_(None)
        )
        if name:
            skill_query = skill_query.filter(StaffSkill.name.ilike(f"%{name}%"))
        for skill in skill_query.order_by(StaffSkill.name.asc()).all():
            skills_by_user.setdefault(skill.user_id, []).append(skill)

    entries = [
        StaffSkillMatrixEntry(
            user_id=u.id,
            user_name=u.name,
            department_id=u.department_id,
            skills=skills_by_user.get(u.id, []),
        )
        for u in users
    ]
    if name:
        entries = [e for e in entries if e.skills]
    return entries


@router.post("/", response_model=StaffSkillOut)
def create_skill(
    payload: StaffSkillCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {sorted(VALID_CATEGORIES)}")
    if payload.proficiency_level is not None and payload.proficiency_level not in VALID_PROFICIENCY_LEVELS:
        raise HTTPException(
            status_code=400, detail=f"Invalid proficiency_level. Must be one of: {sorted(VALID_PROFICIENCY_LEVELS)}"
        )

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skill = StaffSkill(
        **payload.model_dump(),
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    log_activity(
        db=db,
        user=current_user,
        action="staff_skill_created",
        entity_type="staff_skill",
        entity_id=skill.id,
        title=f"{skill.category.capitalize()} added: {skill.name}",
        description=f"Recorded '{skill.name}' for {user.name}.",
    )

    return skill


@router.get("/{skill_id}", response_model=StaffSkillOut)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    skill = db.query(StaffSkill).filter(StaffSkill.id == skill_id, StaffSkill.deleted_at.is_(None)).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.put("/{skill_id}", response_model=StaffSkillOut)
def update_skill(
    skill_id: int,
    payload: StaffSkillUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    skill = db.query(StaffSkill).filter(StaffSkill.id == skill_id, StaffSkill.deleted_at.is_(None)).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates and updates["category"] not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {sorted(VALID_CATEGORIES)}")
    if (
        "proficiency_level" in updates
        and updates["proficiency_level"] is not None
        and updates["proficiency_level"] not in VALID_PROFICIENCY_LEVELS
    ):
        raise HTTPException(
            status_code=400, detail=f"Invalid proficiency_level. Must be one of: {sorted(VALID_PROFICIENCY_LEVELS)}"
        )

    for key, value in updates.items():
        setattr(skill, key, value)

    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}")
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    skill = db.query(StaffSkill).filter(StaffSkill.id == skill_id, StaffSkill.deleted_at.is_(None)).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill.deleted_at = utcnow()
    db.commit()
    return {"message": "Skill removed successfully"}
