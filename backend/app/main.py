from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.db.base
from app.core.config import settings
from app.core.seed import seed_demo_users
from app.db.session import Base, SessionLocal, engine
from app.routes.auth import router as auth_router
from app.routes.clients import router as clients_router
from app.routes.files import router as files_router
from app.routes.protected import router as protected_router
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

@app.get("/")
async def root():
    return {"message": "API is running"}
