"""Independence/conflict-of-interest checking, shared between the
independence-disclosures routes and the staffing (project assignment)
flow in app.routes.projects.

Rule: a disclosure conflicts with a client if the disclosure's client_id
is that client OR any ancestor of it in the client group hierarchy
(Client.parent_client_id) -- staffing someone on a subsidiary matters if
they have a disclosed conflict against the parent holding company, and
vice versa. Disclosures with no client_id (general/firm-wide) are never
auto-matched -- see the model docstring for why.
"""

from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.independence import IndependenceDisclosure

# Guards against a corrupt/circular parent_client_id chain in the data
# turning this into an infinite loop.
MAX_CLIENT_HIERARCHY_DEPTH = 10


def client_hierarchy_ids(db: Session, client_id: int | None) -> list[int]:
    """Returns [client_id, its parent, its grandparent, ...] walking up
    Client.parent_client_id, stopping at the top of the chain or at
    MAX_CLIENT_HIERARCHY_DEPTH, whichever comes first."""
    ids: list[int] = []
    current_id = client_id
    depth = 0
    while current_id is not None and depth < MAX_CLIENT_HIERARCHY_DEPTH:
        if current_id in ids:
            break  # circular parent_client_id data -- stop rather than loop
        ids.append(current_id)
        client = db.query(Client).filter(Client.id == current_id).first()
        if not client:
            break
        current_id = client.parent_client_id
        depth += 1
    return ids


def check_conflicts(db: Session, user_id: int, client_id: int | None) -> list[IndependenceDisclosure]:
    """Active independence disclosures for this user that conflict with
    this client (or its group hierarchy). Returns an empty list if
    client_id is None or no conflicts exist."""
    if client_id is None:
        return []

    hierarchy_ids = client_hierarchy_ids(db, client_id)
    if not hierarchy_ids:
        return []

    return (
        db.query(IndependenceDisclosure)
        .filter(
            IndependenceDisclosure.deleted_at.is_(None),
            IndependenceDisclosure.user_id == user_id,
            IndependenceDisclosure.status == "active",
            IndependenceDisclosure.client_id.in_(hierarchy_ids),
        )
        .order_by(IndependenceDisclosure.created_at.asc())
        .all()
    )
