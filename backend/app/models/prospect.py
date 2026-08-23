from app.core.time import utcnow

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.db.session import Base

# Ordered pipeline stages a prospect moves through on its way to becoming a
# client. "won" and "lost" are terminal -- see app.core.pipeline for the
# transition rules (which stages can move to which) enforced in routes.
PROSPECT_STATUSES = (
    "new",
    "contacted",
    "qualified",
    "proposal_sent",
    "negotiating",
    "won",
    "lost",
)
TERMINAL_PROSPECT_STATUSES = ("won", "lost")

# How the prospect entered the pipeline -- used for BD reporting (which
# channels actually convert) more than for any workflow logic.
PROSPECT_SOURCES = ("referral", "outbound", "inbound", "event", "other")


class Prospect(Base):
    """A potential client, tracked from first contact through to either
    becoming a real Client (see `convert`, below) or being marked lost.
    Deliberately a separate model from Client rather than an early
    Client.status value -- a prospect doesn't have engagements, contacts,
    or billing history yet, and most of its fields (estimated_value,
    expected_close_date, lost_reason) have no meaning once it's a real
    client, so keeping them apart avoids a Client record full of
    permanently-null pipeline fields once won.
    """

    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True, index=True)
    contact_email = Column(String(255), nullable=True, index=True)
    contact_phone = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True, index=True)
    website = Column(String(255), nullable=True)

    source = Column(String(20), nullable=False, default="other", index=True)
    status = Column(String(20), nullable=False, default="new", index=True)

    # Which department would service this engagement if won -- mirrors
    # Client.department_id so scoping (app.core.department_scope) and
    # reporting stay consistent once a prospect converts.
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

    estimated_value = Column(Numeric(12, 2), nullable=True)
    expected_close_date = Column(Date, nullable=True, index=True)

    # The BD owner -- typically a partner or manager driving the
    # relationship. Free-text name/email alongside the FK for the same
    # reason every other actor field in this codebase carries both: the
    # display name survives even if the user record is later removed.
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_to_email = Column(String(255), nullable=True)
    assigned_to_name = Column(String(255), nullable=True)

    # Required when status is set to "lost" -- see app.core.pipeline.
    lost_reason = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    # Set by POST /prospects/{id}/convert once status == "won". Traces
    # the resulting Client back to the prospect that became it, the same
    # lineage pattern as Project.cloned_from_project_id.
    converted_client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    converted_at = Column(DateTime, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)


class ProspectStageEvent(Base):
    """Append-only history of every stage change a prospect goes through,
    kept separate from the mutable `status` column for the same reason
    WorkpaperReviewEvent is kept separate from Workpaper.stage: pipeline
    reporting (win rate, average time-in-stage, where deals stall) needs
    the full transition history, not just the current stage.
    """

    __tablename__ = "prospect_stage_events"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False, index=True)

    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)

    actor_email = Column(String(255), nullable=False)
    actor_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
