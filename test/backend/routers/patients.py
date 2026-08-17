from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.patient_service import PatientService
from backend.schemas.schemas import (
    PatientCreate, PatientUpdate, PatientOut, PatientDetailOut
)

router = APIRouter(prefix="/api/patients", tags=["Patients"])

@router.get("", response_model=List[PatientOut], summary="List and Search Patients")
def get_patients(
    search: Optional[str] = Query(None, description="Search by full name, phone number or email"),
    db: Session = Depends(get_db)
):
    return PatientService.get_patients(db, search=search)

@router.get("/{patient_id}", response_model=PatientDetailOut, summary="Get Patient Details")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = PatientService.get_patient_detail(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED, summary="Create Patient")
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    if not payload.full_name or not payload.full_name.strip():
        raise HTTPException(status_code=400, detail="Patient full name is required.")
    return PatientService.create_patient(db, payload)

@router.put("/{patient_id}", response_model=PatientOut, summary="Update Patient")
def update_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db)):
    updated = PatientService.update_patient(db, patient_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Patient not found or invalid payload.")
    return updated

@router.delete("/{patient_id}", status_code=status.HTTP_200_OK, summary="Delete Patient")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    deleted = PatientService.delete_patient(db, patient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"message": "Patient deleted successfully", "id": patient_id}
