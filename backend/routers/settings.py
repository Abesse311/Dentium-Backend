import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, DB_PATH
from backend.models import ClinicSettings
from backend.schemas import ClinicSettingsResponse, ClinicSettingsUpdate

router = APIRouter()


@router.get(
    "",
    response_model=ClinicSettingsResponse,
    summary="Get clinic settings and operational preferences",
)
def get_clinic_settings(db: Session = Depends(get_db)):
    """Retrieve the clinic's profile and configuration."""
    settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
    if not settings:
        settings = ClinicSettings(
            id=1,
            clinic_name="Cabinet Dentaire",
            doctor_name="Dr. Dentiste",
            phone="",
            address="",
            logo_path=None,
            daily_patient_limit=30,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put(
    "",
    response_model=ClinicSettingsResponse,
    summary="Update clinic settings",
)
@router.patch(
    "",
    response_model=ClinicSettingsResponse,
    summary="Update clinic settings",
)
def update_clinic_settings(
    payload: ClinicSettingsUpdate,
    db: Session = Depends(get_db),
):
    """Update clinic information, doctor profile, and daily capacity limit."""
    settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
    if not settings:
        settings = ClinicSettings(id=1, clinic_name="Cabinet Dentaire")
        db.add(settings)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


@router.get(
    "/backup",
    summary="Download raw SQLite database backup file",
    response_description="Downloads the clinic.db file",
)
def download_backup():
    """Download the current clinic.db SQLite database file for manual backup."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database file not found on disk",
        )
    return FileResponse(
        path=DB_PATH,
        filename="clinic_backup.db",
        media_type="application/octet-stream",
    )
