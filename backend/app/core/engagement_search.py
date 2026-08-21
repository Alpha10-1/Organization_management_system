"""Natural-language-ish search across engagements.

Real semantic search would need an embeddings/LLM backend this codebase
doesn't otherwise depend on; what's built here is the practical middle
ground -- a query like "engagements where we flagged a going concern
issue" is normalized into search terms (dropping stopwords, keeping
known multi-word audit/compliance phrases intact) and matched with
ILIKE across every place an engagement's narrative history lives:
project free-text fields, its client's notes, and its own activity log.
Results are ranked by how many distinct terms matched and how many times,
so "going concern" beats a single stray hit on "concern" alone.

This mirrors the plain keyword search in app.routes.search rather than
replacing it -- that one finds records by name/id, this one finds
engagements by what happened on them.
"""

import re
from collections import defaultdict

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.client import Client
from app.models.client_note import ClientNote
from app.models.project import Project

STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "with",
    "show", "me", "every", "any", "all", "where", "we", "our", "was",
    "were", "is", "are", "did", "has", "have", "had", "that", "this",
    "flagged", "flag", "issue", "issues", "find", "list", "engagement",
    "engagements", "project", "projects",
}

# Domain phrases worth matching as a unit even though each word alone is
# generic (e.g. "concern" alone is noisy, "going concern" is a real term
# of art). Checked case-insensitively against the raw query before
# stopword-stripping, and searched as a single ILIKE phrase.
KNOWN_PHRASES = [
    "going concern",
    "material weakness",
    "related party",
    "significant deficiency",
    "restatement",
    "fraud risk",
    "internal control",
    "scope limitation",
]

TEXT_FIELDS = [
    "description", "objectives", "deliverables", "stakeholders",
    "billing_notes", "close_out_notes", "compliance_flag",
]

RESULT_LIMIT = 20
SNIPPET_RADIUS = 60


def _extract_terms(q: str) -> tuple[list[str], list[str]]:
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


def search_engagements(db: Session, q: str, db_limit: int = 200) -> dict:
    terms, phrases = _extract_terms(q)
    all_needles = phrases + terms

    if not all_needles:
        return {"query": q, "terms": terms, "phrases": phrases, "results": []}

    def _ilike_clause(column):
        return or_(*[column.ilike(f"%{n}%") for n in all_needles])

    project_filters = or_(*[_ilike_clause(getattr(Project, f)) for f in TEXT_FIELDS])
    matched_projects = (
        db.query(Project)
        .filter(Project.deleted_at.is_(None), project_filters)
        .limit(db_limit)
        .all()
    )

    matched_notes = (
        db.query(ClientNote)
        .filter(ClientNote.deleted_at.is_(None), _ilike_clause(ClientNote.body))
        .limit(db_limit)
        .all()
    )

    matched_activity = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.entity_type == "project",
            or_(_ilike_clause(ActivityLog.title), _ilike_clause(ActivityLog.description)),
        )
        .limit(db_limit)
        .all()
    )

    # project_id -> {matched_terms: set, snippets: [str], source_counts: {...}}
    scoreboard: dict[int, dict] = defaultdict(
        lambda: {"matched_terms": set(), "snippets": [], "hit_count": 0}
    )

    def _register(project_id: int, text: str | None, source: str):
        if not text:
            return
        for needle in all_needles:
            if needle.lower() in text.lower():
                entry = scoreboard[project_id]
                entry["matched_terms"].add(needle)
                entry["hit_count"] += 1
                if len(entry["snippets"]) < 3:
                    snippet = _snippet(text, needle)
                    if snippet:
                        entry["snippets"].append(f"[{source}] {snippet}")

    for p in matched_projects:
        for f in TEXT_FIELDS:
            _register(p.id, getattr(p, f), f)

    client_ids_by_project = {p.id: p.client_id for p in matched_projects}
    if matched_notes:
        # Notes are matched by client, but results are engagement-centric,
        # so fan a matched note out to every one of that client's projects
        # (deleted-projects excluded) rather than only ones already in
        # matched_projects.
        note_client_ids = {n.client_id for n in matched_notes}
        client_projects = (
            db.query(Project)
            .filter(Project.deleted_at.is_(None), Project.client_id.in_(note_client_ids))
            .all()
        )
        projects_by_client = defaultdict(list)
        for p in client_projects:
            projects_by_client[p.client_id].append(p)
        for note in matched_notes:
            for p in projects_by_client.get(note.client_id, []):
                _register(p.id, note.body, "client note")

    for entry in matched_activity:
        if entry.entity_id:
            _register(entry.entity_id, entry.title, "activity")
            _register(entry.entity_id, entry.description, "activity")

    if not scoreboard:
        return {"query": q, "terms": terms, "phrases": phrases, "results": []}

    project_ids = list(scoreboard.keys())
    projects = {
        p.id: p
        for p in db.query(Project).filter(Project.id.in_(project_ids), Project.deleted_at.is_(None)).all()
    }
    client_ids = {p.client_id for p in projects.values()}
    clients = {
        c.id: c for c in db.query(Client).filter(Client.id.in_(client_ids), Client.deleted_at.is_(None)).all()
    }

    results = []
    for project_id, entry in scoreboard.items():
        project = projects.get(project_id)
        if project is None:
            continue
        client = clients.get(project.client_id)
        results.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "client_id": project.client_id,
                "client_name": client.display_name if client else None,
                "matched_terms": sorted(entry["matched_terms"]),
                "match_count": entry["hit_count"],
                "snippets": entry["snippets"],
            }
        )

    results.sort(key=lambda r: (len(r["matched_terms"]), r["match_count"]), reverse=True)
    return {"query": q, "terms": terms, "phrases": phrases, "results": results[:RESULT_LIMIT]}
