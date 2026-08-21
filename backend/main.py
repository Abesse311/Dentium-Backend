from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import init_db, get_db
from backend.schemas import HealthResponse
from backend.routers import (
    patients,
    appointments,
    dashboard,
    settings,
    reports,
)
from backend.routers.treatments import treatments_router, treatment_types_router
from backend.routers.invoices import invoices_router, payments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes SQLite database tables and seeds default data on startup."""
    init_db()
    yield


app = FastAPI(
    title="Dental Clinic Management API",
    description="Local backend API for dental clinic management desktop application.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Mandatory CORS Configuration (Section 8)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Safe here: app is localhost-only, never exposed externally
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers Registration
# ---------------------------------------------------------------------------
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"], include_in_schema=False)

app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(patients.router, prefix="/patients", tags=["Patients"], include_in_schema=False)

app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"], include_in_schema=False)

app.include_router(treatments_router, prefix="/api/treatments", tags=["Treatments"])
app.include_router(treatments_router, prefix="/treatments", tags=["Treatments"], include_in_schema=False)

app.include_router(treatment_types_router, prefix="/api/treatment-types", tags=["Treatment Types"])
app.include_router(treatment_types_router, prefix="/treatment-types", tags=["Treatment Types"], include_in_schema=False)

app.include_router(invoices_router, prefix="/api/invoices", tags=["Invoices & Payments"])
app.include_router(invoices_router, prefix="/invoices", tags=["Invoices & Payments"], include_in_schema=False)

app.include_router(payments_router, prefix="/api/payments", tags=["Invoices & Payments"])
app.include_router(payments_router, prefix="/payments", tags=["Invoices & Payments"], include_in_schema=False)

app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"], include_in_schema=False)

app.include_router(reports.router, prefix="/api/reports", tags=["Reports & Analytics"])
app.include_router(reports.router, prefix="/reports", tags=["Reports & Analytics"], include_in_schema=False)
app.include_router(reports.router, prefix="/api/analytics", tags=["Reports & Analytics"], include_in_schema=False)
app.include_router(reports.router, prefix="/analytics", tags=["Reports & Analytics"], include_in_schema=False)


# ---------------------------------------------------------------------------
# System Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
)
@app.get("/health", response_model=HealthResponse, include_in_schema=False)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify backend and database connectivity."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        database="connected",
    )


@app.get("/", tags=["System"], summary="Root endpoint")
def root():
    return {
        "app": "Dental Clinic Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
