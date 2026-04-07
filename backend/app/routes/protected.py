from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.core.fake_db import fake_users_db
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.client import Client
from app.models.file_record import FileRecord
from app.schemas.user import UserPublic

router = APIRouter(tags=["Protected"])


@router.get("/dashboard-summary")
async def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    total_clients = db.query(Client).count()
    total_files = db.query(FileRecord).count()

    active_clients = db.query(Client).filter(Client.status == "Active").count()
    pending_clients = db.query(Client).filter(Client.status == "Pending").count()
    closed_clients = db.query(Client).filter(Client.status == "Closed").count()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_clients_count = (
        db.query(Client).filter(Client.created_at >= seven_days_ago).count()
    )

    recent_clients = (
        db.query(Client)
        .order_by(Client.created_at.desc())
        .limit(5)
        .all()
    )

    recent_activity = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(8)
        .all()
    )

    staff_members = len(fake_users_db)

    status_distribution = [
        {"name": "Active", "value": active_clients},
        {"name": "Pending", "value": pending_clients},
        {"name": "Closed", "value": closed_clients},
    ]

    return {
        "message": current_user.name,
        "role": current_user.role,
        "stats": {
            "total_clients": total_clients,
            "staff_members": staff_members,
            "total_files": total_files,
            "active_clients": active_clients,
            "pending_clients": pending_clients,
            "closed_clients": closed_clients,
            "recent_clients": recent_clients_count,
        },
        "status_distribution": status_distribution,
        "recent_clients": [
            {
                "id": client.id,
                "name": f"{client.first_name} {client.last_name}",
                "status": client.status,
                "email": client.email,
                "phone": client.phone,
                "created_at": client.created_at.isoformat(),
            }
            for client in recent_clients
        ],
        "recent_activity": [
            {
                "id": item.id,
                "action": item.action,
                "entity_type": item.entity_type,
                "title": item.title,
                "description": item.description,
                "user_name": item.user_name,
                "user_email": item.user_email,
                "date": item.created_at.isoformat(),
            }
            for item in recent_activity
        ],
    }


@router.get("/activity-logs")
async def activity_logs(
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    items = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": item.id,
            "action": item.action,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "title": item.title,
            "description": item.description,
            "user_name": item.user_name,
            "user_email": item.user_email,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]