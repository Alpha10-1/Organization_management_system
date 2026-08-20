from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class Workpaper(Base):
    """A single piece of audit/engagement evidence (e.g. a fieldwork test,
    a substantive-testing schedule, a reconciliation) moving through the
    preparer -> reviewer -> partner review chain. This is the same
    sign-off pattern already used for client-facing Milestones, applied
    one level down to internal deliverables that clients never see.

    `stage` always reflects where the workpaper currently sits; the full
    history of who did what and why lives in WorkpaperReviewEvent below,
    which is what makes this useful for QC/PCAOB-style review later --
    "who reviewed this, when, and what did they say" needs to survive a
    rejection-and-rework cycle, not just show the latest state.
    """

    __tablename__ = "workpapers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("file_records.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Free-text engagement area, e.g. "fieldwork", "substantive_testing",
    # "analytics", "documentation" -- deliberately not a hard enum since
    # different engagement types (audit/tax/advisory) use different
    # vocabularies here.
    category = Column(String(100), nullable=True, index=True)

    # in_preparation | pending_review | pending_partner_signoff | complete
    # A rejection at either review stage sends the workpaper back to
    # in_preparation rather than introducing a separate "rejected" stage
    # -- rejection is a transient event (see WorkpaperReviewEvent), not a
    # resting state.
    stage = Column(String(30), nullable=False, default="in_preparation", index=True)

    preparer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prepared_by_email = Column(String(255), nullable=False)
    prepared_by_name = Column(String(255), nullable=False)
    submitted_for_review_at = Column(DateTime, nullable=True)

    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    review_status = Column(String(20), nullable=True)  # approved | rejected (latest outcome)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_email = Column(String(255), nullable=True)
    reviewed_by_name = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)

    partner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    partner_status = Column(String(20), nullable=True)  # approved | rejected (latest outcome)
    partner_signed_off_at = Column(DateTime, nullable=True)
    partner_by_email = Column(String(255), nullable=True)
    partner_by_name = Column(String(255), nullable=True)
    partner_notes = Column(Text, nullable=True)

    created_by_email = Column(String(255), nullable=False)
    created_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)


class WorkpaperReviewEvent(Base):
    """Append-only history of everything that has happened to a workpaper
    as it moves through the review chain. Kept separate from the mutable
    fields on Workpaper itself so a rejection-and-resubmit cycle (which
    real workpapers go through constantly) doesn't destroy the record of
    the earlier rounds."""

    __tablename__ = "workpaper_review_events"

    id = Column(Integer, primary_key=True, index=True)
    workpaper_id = Column(Integer, ForeignKey("workpapers.id"), nullable=False, index=True)

    # submitted_for_review | review_approved | review_rejected |
    # partner_approved | partner_rejected | reopened
    event_type = Column(String(30), nullable=False, index=True)
    notes = Column(Text, nullable=True)

    actor_email = Column(String(255), nullable=False)
    actor_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
