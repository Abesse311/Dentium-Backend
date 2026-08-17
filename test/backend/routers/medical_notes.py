from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.models.medical_note import MedicalNote
from backend.models.patient import Patient
from backend.schemas.schemas import MedicalNoteCreate, MedicalNoteOut

router = APIRouter(prefix="/api/patients/{patient_id}/medical-notes", tags=["Medical Notes"])

@router.get("", response_model=List[MedicalNoteOut], summary="List Patient Medical Notes")
def get_medical_notes(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    notes = db.query(MedicalNote).filter(
        MedicalNote.patient_id == patient_id
    ).order_by(desc(MedicalNote.created_at)).all()

    return [MedicalNoteOut.model_validate(n) for n in notes]

@router.post("", response_model=MedicalNoteOut, status_code=status.HTTP_201_CREATED, summary="Add Patient Medical Note")
def create_medical_note(patient_id: int, payload: MedicalNoteCreate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if not payload.note or not payload.note.strip():
        raise HTTPException(status_code=400, detail="Medical note content cannot be empty.")

    medical_note = MedicalNote(
        patient_id=patient_id,
        note=payload.note.strip()
    )
    db.add(medical_note)
    db.commit()
    db.refresh(medical_note)
    return MedicalNoteOut.model_validate(medical_note)
