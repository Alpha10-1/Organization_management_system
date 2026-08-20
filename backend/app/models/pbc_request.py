from app.core.time import utcnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.session import Base


class PBCRequest(Base):
    """A single "prepared by client" checklist line: a document or piece of
    information staff need from the client for a given engagement (e.g.
    "Q4 trial balance", "signed bank confirmation letter"), with a due date
    and a status the client can move by uploading against it in the portal.

    Deliberately its own model rather than reusing TaskTemplate/Task --
    those model internal work with an assignee from `users`; a PBC item's
    "assignee" is the client, tracked via ClientPortalUser, and its
    lifecycle (requested -> submitted -> approved/rejected) doesn't map
    onto internal task status. It's the same *idea* as a task template
    checklist applied one level down, just modeled directly against the
    project instead of going through the template/apply machinery, since
    PBC lists are typically engagement-specific rather than cloned from a
    firm-wide standard list.
    """

    __tablename__ = "pbc_requests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Free-text grouping label (e.g. "Financial Statements", "Payroll",
    # "Tax") so a long PBC list can be organized into sections in the
    # portal UI without a separate categories table.
    category = Column(String(100), nullable=True, index=True)
    due_date = Column(DateTime, nullable=True, index=True)

    # requested (nothing from the client yet) | submitted (client uploaded
    # something, awaiting staff review) | approved (staff accepted it) |
    # rejected (staff needs something different -- see review_notes)
    status = Column(String(20), nullable=False, default="requested", index=True)

    # Points at the most recently uploaded FileRecord satisfying this
    # request. A client re-uploading (e.g. after a rejection) overwrites
    # this pointer to the newest file rather than accumulating a list --
    # FileRecord's own version chain (previous_version_id) still preserves
    # history if the same file slot is reused.
    file_id = Column(Integer, ForeignKey("file_records.id"), nullable=True, index=True)

    submitted_at = Column(DateTime, nullable=True)
    submitted_by_email = Column(String(255), nullable=True)
    submitted_by_name = Column(String(255), nullable=True)

    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_email = Column(String(255), nullable=True)
    reviewed_by_name = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)

    requested_by_email = Column(String(255), nullable=False)
    requested_by_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
