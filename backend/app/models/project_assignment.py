from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.db.session import Base


class ProjectAssignment(Base):
    """Assigns a project/engagement to either an individual user or an
    entire department. Exactly one of user_id / department_id is set
    (enforced in app.routes.projects) -- assigning a department means every
    member of that department is considered staffed on the engagement,
    without having to add each person individually.
    """

    __tablename__ = "project_assignments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

    # Free-text role on the engagement, e.g. "Team Member", "Reviewer",
    # "Field Lead". Optional -- most assignments don't need one.
    role = Column(String(100), nullable=True)

    assigned_by_email = Column(String(255), nullable=False)
    assigned_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
