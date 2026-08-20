from app.core.time import utcnow

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.db.session import Base


class ClientPortalUser(Base):
    """A login account for someone at a client organization to access the
    client portal (view milestone status, respond to PBC requests, sign off
    on deliverables). Deliberately a separate table/auth path from `User`
    (internal staff) rather than a shared table with a role flag -- a client
    login must never be able to authenticate against internal staff routes,
    and keeping the tables (and JWTs) distinct makes that a structural
    guarantee rather than a permission check that could be missed on some
    endpoint. See app.core.portal_deps for the parallel auth dependency.

    Optionally linked to a ClientContact (the "real world" record of who
    this person is at the client), but not required -- a firm may want to
    invite someone to the portal before a formal contact record exists.
    """

    __tablename__ = "client_portal_users"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    client_contact_id = Column(Integer, ForeignKey("client_contacts.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    disabled = Column(Boolean, nullable=False, default=False)

    # Set by whoever on staff invited this person -- surfaced on the
    # portal-users admin list so it's clear who to ask if a client can't
    # log in.
    invited_by_email = Column(String(255), nullable=False)
    invited_by_name = Column(String(255), nullable=False)

    # Password reset AND initial account activation both flow through this
    # same token pair -- an invite is just a reset token issued before any
    # password has ever been set (see routes/portal_auth.py), so there's no
    # separate "activation token" concept to keep in sync.
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    last_login_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
