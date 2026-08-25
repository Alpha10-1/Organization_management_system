"""Firm-wide knowledge base: aggregates every engagement's close-out
retrospective (Project.close_out_notes) into one searchable "how did we
handle this before" resource, instead of leaving each one siloed on its
own completed engagement where nobody would think to look for it.

Deliberately a read-only view over existing data rather than a new
model -- close_out_notes already is the retrospective; this just makes
the whole firm's history of them findable by engagement type, client
industry, compliance area, or free-text search, the way
app.core.engagement_search makes an individual engagement's full
narrative history findable. The two overlap in data source but not
intent: engagement_search treats close_out_notes as one signal among
many on a specific engagement; this module treats the notes themselves
as the primary content, browsable and searchable across the firm.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.engagement_search import KNOWN_PHRASES, STOPWORDS
from app.models.client import Client
from app.models.project import Project

RESULT_LIMIT = 50
SNIPPET_RADIUS = 100


def _extract_terms(q: str) -> tuple[list[str], list[str]]:
    """Reuses the same term/phrase extraction as engagement_search so a
    query like "going concern" behaves consistently whether it's typed
    into engagement search or the knowledge base."""
    lowered = q.lower()
    phrases = [p for p in KNOWN_PHRASES if p in lowered]
    for p in phrases:
        lowered = lowered.replace(p, " ")

    words = re.findall(r"[a-z0-9]+", lowered)
    terms = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return terms, phrases


def _snippet(text: str, term: str) -> str | None:
    idx = text.lower().find(term.lower())
    if idx == -1:
        return None
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(text), idx + len(term) + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


@dataclass
class KnowledgeBaseEntry:
    project_id: int
    project_name: str
    engagement_type: str
    risk_level: str
    compliance_flag: str | None
    client_id: int
    client_name: str | None
    client_industry: str | None
    engagement_partner_name: str | None
    closed_out_at: object  # datetime | None, project.updated_at as a proxy for "when this was written"
    close_out_notes: str
    matched_terms: list[str] = field(default_factory=list)
    snippet: str | None = None


def _base_query(db: Session):
    return (
        db.query(Project, Client)
        .join(Client, Client.id == Project.client_id)
        .filter(
            Project.deleted_at.is_(None),
            Client.deleted_at.is_(None),
            Project.close_out_notes.isnot(None),
            Project.close_out_notes != "",
        )
    )


def search_knowledge_base(
    db: Session,
    q: str | None = None,
    engagement_type: str | None = None,
    industry: str | None = None,
    compliance_flag: str | None = None,
    risk_level: str | None = None,
    client_id: int | None = None,
    limit: int = RESULT_LIMIT,
) -> list[KnowledgeBaseEntry]:
    query = _base_query(db)

    if engagement_type:
        query = query.filter(Project.type == engagement_type)
    if industry:
        query = query.filter(Client.industry == industry)
    if compliance_flag:
        query = query.filter(Project.compliance_flag == compliance_flag)
    if risk_level:
        query = query.filter(Project.risk_level == risk_level)
    if client_id is not None:
        query = query.filter(Project.client_id == client_id)

    terms: list[str] = []
    phrases: list[str] = []
    if q and q.strip():
        terms, phrases = _extract_terms(q)
        needles = phrases + terms
        if needles:
            query = query.filter(
                or_(*[Project.close_out_notes.ilike(f"%{n}%") for n in needles])
            )

    rows = query.order_by(Project.updated_at.desc()).limit(500).all()

    needles = phrases + terms
    entries: list[KnowledgeBaseEntry] = []
    for project, client in rows:
        matched = [n for n in needles if n.lower() in (project.close_out_notes or "").lower()]
        snippet = None
        if matched:
            snippet = _snippet(project.close_out_notes, matched[0])

        entries.append(
            KnowledgeBaseEntry(
                project_id=project.id,
                project_name=project.name,
                engagement_type=project.type,
                risk_level=project.risk_level,
                compliance_flag=project.compliance_flag,
                client_id=client.id,
                client_name=client.display_name,
                client_industry=client.industry,
                engagement_partner_name=project.engagement_partner_name,
                closed_out_at=project.updated_at,
                close_out_notes=project.close_out_notes,
                matched_terms=sorted(set(matched)),
                snippet=snippet,
            )
        )

    if needles:
        entries.sort(key=lambda e: len(e.matched_terms), reverse=True)

    return entries[:limit]


def get_knowledge_base_facets(db: Session) -> dict:
    """Distinct filter values among engagements that actually have a
    close-out note, so the UI only ever offers filter options that will
    return results."""
    rows = _base_query(db).all()

    types = sorted({p.type for p, _c in rows if p.type})
    industries = sorted({c.industry for _p, c in rows if c.industry})
    compliance_flags = sorted({p.compliance_flag for p, _c in rows if p.compliance_flag})
    risk_levels = sorted({p.risk_level for p, _c in rows if p.risk_level})

    return {
        "engagement_types": types,
        "industries": industries,
        "compliance_flags": compliance_flags,
        "risk_levels": risk_levels,
        "total_entries": len(rows),
    }
