from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.core.knowledge_base import get_knowledge_base_facets, search_knowledge_base
from app.db.session import get_db
from app.schemas.knowledge_base import (
    KnowledgeBaseFacetsOut,
    KnowledgeBaseSearchOut,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


@router.get("/", response_model=KnowledgeBaseSearchOut)
def browse_knowledge_base(
    q: str | None = Query(default=None, min_length=1),
    engagement_type: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    compliance_flag: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    client_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Firm-wide close-out retrospectives: browse (no filters) or search
    (q + optional filters) every completed engagement's lessons-learned
    notes, regardless of which client or department ran it. Read-only --
    close_out_notes is still edited on the engagement itself.
    """
    results = search_knowledge_base(
        db,
        q=q,
        engagement_type=engagement_type,
        industry=industry,
        compliance_flag=compliance_flag,
        risk_level=risk_level,
        client_id=client_id,
    )
    return KnowledgeBaseSearchOut(query=q, results=results)


@router.get("/facets", response_model=KnowledgeBaseFacetsOut)
def get_facets(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Distinct engagement type / industry / compliance flag / risk level
    values actually present among engagements with a close-out note --
    drives the filter dropdowns without ever offering an empty filter."""
    return get_knowledge_base_facets(db)
