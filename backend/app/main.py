from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.db.base
from app.db.session import Base, engine
from app.routes.auth import router as auth_router
from app.routes.clients import router as clients_router
from app.routes.files import router as files_router
from app.routes.protected import router as protected_router
from app.routes.users import router as users_router

app = FastAPI(title="Organization Management System API")

# Create database tables from registered models on startup
Base.metadata.create_all(bind=engine)

# Allow local frontend apps to access the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(protected_router)
app.include_router(clients_router)
app.include_router(files_router)
app.include_router(users_router)

@app.get("/")
async def root():
    return {"message": "API is running"}
