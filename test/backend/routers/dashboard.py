from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.appointment_service import AppointmentService
from backend.schemas.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("", response_model=DashboardStats, summary="Get Dashboard Analytics and Today's Agenda")
def get_dashboard_stats(db: Session = Depends(get_db)):
    return AppointmentService.get_dashboard_stats(db)
