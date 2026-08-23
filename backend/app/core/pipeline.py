"""Stage-transition rules for the BD pipeline (Prospect -> Proposal ->
Client), kept separate from the route handlers the same way independence
and billing logic are -- so the rules are unit-testable and reusable if a
second entry point (e.g. a bulk-import job) ever needs them.
"""

from fastapi import HTTPException, status

from app.models.prospect import PROSPECT_STATUSES, TERMINAL_PROSPECT_STATUSES
from app.models.proposal import PROPOSAL_STATUSES

# Forward-only pipeline: each stage can only advance to the stages listed,
# or be marked lost at any non-terminal point (a deal can die at any
# stage, not just at the end). Terminal statuses (won/lost) have no
# outbound transitions -- reopening a closed deal means creating a new
# Prospect record, not resurrecting the old one, so pipeline reporting
# (win rate, time-in-stage) stays accurate.
ALLOWED_PROSPECT_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("contacted", "lost"),
    "contacted": ("qualified", "lost"),
    "qualified": ("proposal_sent", "lost"),
    "proposal_sent": ("negotiating", "won", "lost"),
    "negotiating": ("won", "lost"),
    "won": (),
    "lost": (),
}

ALLOWED_PROPOSAL_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("sent",),
    "sent": ("accepted", "rejected", "expired"),
    "accepted": (),
    "rejected": (),
    "expired": (),
}


def validate_prospect_status(status_value: str) -> None:
    if status_value not in PROSPECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(PROSPECT_STATUSES)}",
        )


def validate_proposal_status(status_value: str) -> None:
    if status_value not in PROPOSAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(PROPOSAL_STATUSES)}",
        )


def require_valid_prospect_transition(current: str, target: str) -> None:
    validate_prospect_status(target)
    if current in TERMINAL_PROSPECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prospect is already {current} and cannot change status",
        )
    allowed = ALLOWED_PROSPECT_TRANSITIONS.get(current, ())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move a prospect from '{current}' to '{target}'. "
            f"Allowed next stage(s): {', '.join(allowed) or 'none (terminal)'}",
        )


def require_valid_proposal_transition(current: str, target: str) -> None:
    validate_proposal_status(target)
    allowed = ALLOWED_PROPOSAL_TRANSITIONS.get(current, ())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move a proposal from '{current}' to '{target}'. "
            f"Allowed next status(es): {', '.join(allowed) or 'none (terminal)'}",
        )
