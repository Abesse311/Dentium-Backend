from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import engine, Base, get_db
from backend.config import APP_NAME, APP_VERSION, APP_DESCRIPTION, CONTACT_EMAIL, DB_PATH
import backend.models  # noqa: F401 – registers all ORM models
from backend.routers import patients, appointments, medical_notes, dashboard
from backend.services.seed_data import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed demo data on first launch."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    contact={"name": "Clinic Support", "email": CONTACT_EMAIL},
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(dashboard.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(medical_notes.router)


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check",
    response_description="Returns ok when the server is running.",
)
def health_check():
    return {"status": "ok", "version": APP_VERSION}


@app.get(
    "/api/version",
    tags=["System"],
    summary="Application version and build info",
)
def version_info():
    import sys
    import sqlite3
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "python": sys.version,
        "sqlite": sqlite3.sqlite_version,
        "db_path": str(DB_PATH),
    }


@app.post(
    "/api/seed",
    tags=["System"],
    summary="Seed demo dataset",
    response_description="Skipped if data already exists, unless force=true.",
)
def seed_database(force: bool = False, db: Session = Depends(get_db)):
    return seed_initial_data(db, force=force)
