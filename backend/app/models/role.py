from app.core.time import utcnow

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from app.db.session import Base


class Role(Base):
    """A custom, admin-managed role that grants a specific set of
    firm-wide permissions (see app.core.permissions.PERMISSION_CATALOG)
    to whichever staff members are assigned it via User.custom_role_id.

    This sits *alongside* the existing User.role column (admin/staff),
    not in place of it -- admin/staff still governs the coarse
    authentication tier (and admin always has every permission,
    unconditionally, regardless of any role assignment). A custom role
    is how a "staff" user gets delegated a slice of admin-level
    authority -- e.g. a Partner who can approve any leave request and
    override independence conflicts without being a full admin able to
    create accounts or change anyone's system role. Role/permission
    management itself (this table) is intentionally never delegable
    through the permission system it defines -- only an admin can
    create, edit, delete, or assign roles (enforced in
    app.routes.roles), and a handful of especially sensitive actions
    (changing someone's system role, disabling self-lockout guards)
    stay hard-coded to admin-only regardless of any permission granted
    here.
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # list[str] of permission keys from PERMISSION_CATALOG. Stored as
    # JSON rather than a join table -- there's no need to query "which
    # roles grant permission X" at the database level; every check is
    # "does this user's role's permission list contain key Y", which is
    # just as fast done in Python after a single row fetch.
    permissions = Column(JSON, nullable=False, default=list)

    # Seeded defaults (Partner, Manager, Engagement Quality Reviewer) --
    # editable like any other role, but protected from deletion so a
    # firm always has at least a starting point to customize rather than
    # build from nothing.
    is_system = Column(Boolean, nullable=False, default=False)

    created_by_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
