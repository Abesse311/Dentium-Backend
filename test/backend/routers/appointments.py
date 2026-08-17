from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.appointment_service import AppointmentService
from backend.schemas.schemas import (
    AppointmentCreate, AppointmentUpdate, AppointmentOut
)

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

@router.get("", response_model=List[AppointmentOut], summary="List and Filter Appointments")
def get_appointments(
    date_filter: Optional[str] = Query(None, alias="date", description="Filter by date (YYYY-MM-DD)"),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by appointment type"),
    db: Session = Depends(get_db)
):
    return AppointmentService.get_appointments(
        db,
        date_str=date_filter,
        patient_id=patient_id,
        status_val=status_filter,
        type_val=type_filter
    )

@router.get("/today", response_model=List[AppointmentOut], summary="Get Today's Appointments")
def get_today_appointments(db: Session = Depends(get_db)):
    return AppointmentService.get_today_appointments(db)

@router.get("/{appointment_id}", response_model=AppointmentOut, summary="Get Appointment Details")
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    apt = AppointmentService.get_appointment(db, appointment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return apt

@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED, summary="Create Appointment")
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    apt = AppointmentService.create_appointment(db, payload)
    if not apt:
        raise HTTPException(
            status_code=400,
            detail="Could not create appointment. Please check if the patient exists and all required fields are valid."
        )
    return apt

@router.put("/{appointment_id}", response_model=AppointmentOut, summary="Update Appointment")
def update_appointment(appointment_id: int, payload: AppointmentUpdate, db: Session = Depends(get_db)):
    updated = AppointmentService.update_appointment(db, appointment_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found or invalid patient ID.")
    return updated

@router.delete("/{appointment_id}", status_code=status.HTTP_200_OK, summary="Delete Appointment")
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    deleted = AppointmentService.delete_appointment(db, appointment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Appointment deleted successfully", "id": appointment_id}
