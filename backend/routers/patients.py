from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Patient, Treatment, Invoice
from backend.schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    TreatmentResponse,
    InvoiceResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient record in the database."""
    patient = Patient(
        full_name=payload.full_name,
        phone=payload.phone,
        birth_date=payload.birth_date,
        gender=payload.gender,
        address=payload.address,
        medical_history=payload.medical_history,
        notes=payload.notes,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get(
    "",
    response_model=List[PatientResponse],
    summary="List and search patients",
)
def list_patients(
    search: Optional[str] = Query(
        None,
        description="Search term to partially match against patient full_name or phone",
    ),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Max number of patients to return"),
    db: Session = Depends(get_db),
):
    """Retrieve a list of patients, optionally filtered by name or phone."""
    query = db.query(Patient)

    if search:
        search_clean = search.strip()
        search_pattern = f"%{search_clean}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(search_pattern),
                Patient.phone.ilike(search_pattern),
            )
        )

    patients = query.order_by(Patient.created_at.desc(), Patient.id.desc()).offset(skip).limit(limit).all()
    return patients


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient details",
)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """Get complete details of a specific patient by ID."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )
    return patient


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient details",
)
@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Partially update patient details",
)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
):
    """Update fields of an existing patient."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a patient",
)
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    """Delete a patient and cascade delete all their appointments, treatments, and invoices."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )

    db.delete(patient)
    db.commit()
    return {"message": f"Patient with ID {patient_id} deleted successfully", "id": patient_id}


@router.get(
    "/{patient_id}/treatments",
    response_model=List[TreatmentResponse],
    summary="Get patient's full treatment history",
)
def get_patient_treatments(patient_id: int, db: Session = Depends(get_db)):
    """Get all treatments recorded for a patient, ordered chronologically."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )

    treatments = (
        db.query(Treatment)
        .options(joinedload(Treatment.treatment_type))
        .filter(Treatment.patient_id == patient_id)
        .order_by(Treatment.treatment_date.desc(), Treatment.id.desc())
        .all()
    )
    return treatments


@router.get(
    "/{patient_id}/invoices",
    response_model=List[InvoiceResponse],
    summary="Get patient's full invoice and payment history",
)
def get_patient_invoices(
    patient_id: int,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by invoice status: 'unpaid', 'partially_paid', 'paid'",
    ),
    date_filter: Optional[date] = Query(None, alias="date", description="Filter invoices for an exact single date (YYYY-MM-DD)"),
    date_from: Optional[date] = Query(None, description="Filter invoices from date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter invoices to date (inclusive)"),
    start_date: Optional[date] = Query(None, description="Alias for date_from"),
    end_date: Optional[date] = Query(None, description="Alias for date_to"),
    db: Session = Depends(get_db),
):
    """Get all invoices (including line items and payments) for a patient with optional date & status filters."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )

    query = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.items),
            joinedload(Invoice.payments),
        )
        .filter(Invoice.patient_id == patient_id)
    )

    effective_from = date_from or start_date
    effective_to = date_to or end_date

    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if date_filter is not None:
        query = query.filter(Invoice.invoice_date == date_filter)
    if effective_from is not None:
        query = query.filter(Invoice.invoice_date >= effective_from)
    if effective_to is not None:
        query = query.filter(Invoice.invoice_date <= effective_to)

    invoices = (
        query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        .all()
    )
    return invoices
