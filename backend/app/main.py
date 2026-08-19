from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.db.base
from app.core.config import settings
from app.core.seed import seed_demo_users
from app.db.session import Base, SessionLocal, engine
from app.routes.auth import router as auth_router
from app.routes.change_orders import router as change_orders_router
from app.routes.clients import router as clients_router
from app.routes.comments import router as comments_router
from app.routes.contracts import router as contracts_router
from app.routes.departments import router as departments_router
from app.routes.files import router as files_router
from app.routes.independence import router as independence_router
from app.routes.invoices import router as invoices_router
from app.routes.leave_requests import router as leave_requests_router
from app.routes.milestones import router as milestones_router
from app.routes.notifications import router as notifications_router
from app.routes.projects import router as projects_router
from app.routes.protected import router as protected_router
from app.routes.reports import router as reports_router
from app.routes.resource_requests import router as resource_requests_router
from app.routes.search import router as search_router
from app.routes.skills import router as skills_router
from app.routes.tags import router as tags_router
from app.routes.task_templates import router as task_templates_router
from app.routes.tasks import router as tasks_router
from app.routes.time_entries import router as time_entries_router
from app.routes.users import router as users_router

app = FastAPI(title="Organization Management System API")

# Create database tables from registered models on startup
Base.metadata.create_all(bind=engine)

# Seed demo accounts on first run only (no-op if users already exist)
with SessionLocal() as db:
    seed_demo_users(db)

# Allowed origins come from CORS_ORIGINS (comma-separated) so this can be
# tightened/loosened per deployment without a code change. Falls back to
# localhost defaults for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(auth_router)
app.include_router(protected_router)
app.include_router(clients_router)
app.include_router(files_router)
app.include_router(users_router)
app.include_router(departments_router)
app.include_router(projects_router)
app.include_router(tags_router)
app.include_router(tasks_router)
app.include_router(task_templates_router)
app.include_router(milestones_router)
app.include_router(contracts_router)
app.include_router(change_orders_router)
app.include_router(time_entries_router)
app.include_router(invoices_router)
app.include_router(notifications_router)
app.include_router(comments_router)
app.include_router(search_router)
app.include_router(reports_router)
app.include_router(skills_router)
app.include_router(resource_requests_router)
app.include_router(leave_requests_router)
app.include_router(independence_router)

@app.get("/")
async def root():
    return {"message": "API is running"}
