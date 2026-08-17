from datetime import date
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Treatment, TreatmentType, Patient, Appointment
from backend.schemas import (
    TreatmentCreate,
    TreatmentUpdate,
    TreatmentResponse,
    TreatmentTypeCreate,
    TreatmentTypeUpdate,
    TreatmentTypeResponse,
)

treatments_router = APIRouter()
treatment_types_router = APIRouter()


# ===========================================================================
# 1. Treatment Types Catalog Endpoints (/api/treatment-types)
# ===========================================================================
@treatment_types_router.get(
    "",
    response_model=List[TreatmentTypeResponse],
    summary="List all treatment types in the catalog",
)
def list_treatment_types(
    category: Optional[Literal["general", "per_tooth"]] = Query(
        None,
        description="Filter by category: 'general' (soins généraux) or 'per_tooth' (soins par dent)",
    ),
    db: Session = Depends(get_db),
):
    """Retrieve treatment types with French names, categories, and default prices."""
    query = db.query(TreatmentType)
    if category:
        query = query.filter(TreatmentType.category == category)
    return query.order_by(TreatmentType.id.asc()).all()


@treatment_types_router.post(
    "",
    response_model=TreatmentTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new treatment type to the catalog",
)
def create_treatment_type(payload: TreatmentTypeCreate, db: Session = Depends(get_db)):
    """Create a new procedure type in the clinic's catalog."""
    treatment_type = TreatmentType(
        category=payload.category,
        name=payload.name,
        default_price=payload.default_price,
        description=payload.description,
    )
    db.add(treatment_type)
    db.commit()
    db.refresh(treatment_type)
    return treatment_type


@treatment_types_router.get(
    "/{treatment_type_id}",
    response_model=TreatmentTypeResponse,
    summary="Get single treatment type by ID",
)
def get_treatment_type(treatment_type_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a specific treatment type from catalog."""
    tt = db.query(TreatmentType).filter(TreatmentType.id == treatment_type_id).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment type with ID {treatment_type_id} not found",
        )
    return tt


@treatment_types_router.put(
    "/{treatment_type_id}",
    response_model=TreatmentTypeResponse,
    summary="Update a treatment type in the catalog",
)
@treatment_types_router.patch(
    "/{treatment_type_id}",
    response_model=TreatmentTypeResponse,
    summary="Partially update a treatment type in the catalog",
)
def update_treatment_type(
    treatment_type_id: int,
    payload: TreatmentTypeUpdate,
    db: Session = Depends(get_db),
):
    """Update name, default price, or description of a treatment type."""
    tt = db.query(TreatmentType).filter(TreatmentType.id == treatment_type_id).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment type with ID {treatment_type_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tt, field, value)

    db.commit()
    db.refresh(tt)
    return tt


@treatment_types_router.delete(
    "/{treatment_type_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a treatment type from the catalog",
)
def delete_treatment_type(treatment_type_id: int, db: Session = Depends(get_db)):
    """Delete a treatment type from catalog if not currently referenced in treatments."""
    tt = db.query(TreatmentType).filter(TreatmentType.id == treatment_type_id).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment type with ID {treatment_type_id} not found",
        )

    # Check if in use
    in_use_count = db.query(Treatment).filter(Treatment.treatment_type_id == treatment_type_id).count()
    if in_use_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete treatment type '{tt.name}' because it is referenced by {in_use_count} clinical treatment record(s)",
        )

    db.delete(tt)
    db.commit()
    return {"message": f"Treatment type '{tt.name}' deleted successfully", "id": treatment_type_id}


# ===========================================================================
# 2. Treatments (Odontogram / Clinical Records) Endpoints (/api/treatments)
# ===========================================================================
@treatments_router.post(
    "",
    response_model=TreatmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new dental treatment",
)
def create_treatment(payload: TreatmentCreate, db: Session = Depends(get_db)):
    """Create a new treatment record linked to a patient, optional tooth (FDI 11-48), and treatment type."""
    # 1. Validate patient existence
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {payload.patient_id} not found",
        )

    # 2. Validate treatment type existence
    tt = db.query(TreatmentType).filter(TreatmentType.id == payload.treatment_type_id).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment type with ID {payload.treatment_type_id} not found",
        )

    # 3. Cross-validate category vs tooth_number
    if tt.category == "general" and payload.tooth_number is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le soin général '{tt.name}' ne peut pas être associé à une dent spécifique (tooth_number doit être NULL)",
        )
    if tt.category == "per_tooth" and payload.tooth_number is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le soin par dent '{tt.name}' nécessite un numéro de dent FDI valide (11-48)",
        )

    # 4. Validate optional appointment
    if payload.appointment_id is not None:
        appointment = db.query(Appointment).filter(Appointment.id == payload.appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {payload.appointment_id} not found",
            )
        if appointment.patient_id != payload.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appointment #{payload.appointment_id} belongs to patient #{appointment.patient_id}, not patient #{payload.patient_id}",
            )

    # 5. Fallback price to default catalog price if omitted
    price = payload.price if payload.price is not None else tt.default_price
    treatment_date = payload.treatment_date or date.today()

    treatment = Treatment(
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
        treatment_type_id=payload.treatment_type_id,
        tooth_number=payload.tooth_number,
        status=payload.status or "planned",
        price=price,
        treatment_date=treatment_date,
        notes=payload.notes,
    )
    db.add(treatment)
    db.commit()
    db.refresh(treatment)

    treatment.patient = patient
    treatment.treatment_type = tt
    return treatment


@treatments_router.get(
    "",
    response_model=List[TreatmentResponse],
    summary="List and filter treatments across patients",
)
def list_treatments(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: 'planned', 'in_progress', 'completed'",
    ),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    tooth_number: Optional[int] = Query(None, ge=11, le=48, description="Filter by FDI tooth number"),
    treatment_type_id: Optional[int] = Query(None, description="Filter by treatment type catalog ID"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(200, ge=1, le=1000, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """List treatments with support for filtering by planned status, patient, or tooth."""
    query = (
        db.query(Treatment)
        .options(
            joinedload(Treatment.treatment_type),
            joinedload(Treatment.patient),
        )
    )

    if status_filter:
        query = query.filter(Treatment.status == status_filter)
    if patient_id is not None:
        query = query.filter(Treatment.patient_id == patient_id)
    if tooth_number is not None:
        query = query.filter(Treatment.tooth_number == tooth_number)
    if treatment_type_id is not None:
        query = query.filter(Treatment.treatment_type_id == treatment_type_id)

    treatments = (
        query.order_by(Treatment.treatment_date.desc(), Treatment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return treatments


@treatments_router.get(
    "/{treatment_id}",
    response_model=TreatmentResponse,
    summary="Get treatment details by ID",
)
def get_treatment(treatment_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a single treatment record."""
    treatment = (
        db.query(Treatment)
        .options(
            joinedload(Treatment.treatment_type),
            joinedload(Treatment.patient),
        )
        .filter(Treatment.id == treatment_id)
        .first()
    )
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment with ID {treatment_id} not found",
        )
    return treatment


@treatments_router.patch(
    "/{treatment_id}",
    response_model=TreatmentResponse,
    summary="Update treatment details",
)
@treatments_router.put(
    "/{treatment_id}",
    response_model=TreatmentResponse,
    summary="Update treatment details",
)
def update_treatment(
    treatment_id: int,
    payload: TreatmentUpdate,
    db: Session = Depends(get_db),
):
    """Update treatment status (planned, in_progress, completed), tooth, price, date, or notes."""
    treatment = (
        db.query(Treatment)
        .options(
            joinedload(Treatment.treatment_type),
            joinedload(Treatment.patient),
        )
        .filter(Treatment.id == treatment_id)
        .first()
    )
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment with ID {treatment_id} not found",
        )

    # Validate treatment_type if changed
    if payload.treatment_type_id is not None and payload.treatment_type_id != treatment.treatment_type_id:
        tt = db.query(TreatmentType).filter(TreatmentType.id == payload.treatment_type_id).first()
        if not tt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Treatment type with ID {payload.treatment_type_id} not found",
            )
        treatment.treatment_type = tt

    # Validate appointment if changed
    if payload.appointment_id is not None and payload.appointment_id != treatment.appointment_id:
        apt = db.query(Appointment).filter(Appointment.id == payload.appointment_id).first()
        if not apt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {payload.appointment_id} not found",
            )
        if apt.patient_id != treatment.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appointment #{payload.appointment_id} belongs to patient #{apt.patient_id}, not #{treatment.patient_id}",
            )

    update_data = payload.model_dump(exclude_unset=True)

    # Cross-validate category vs tooth_number
    target_tt_id = payload.treatment_type_id if payload.treatment_type_id is not None else treatment.treatment_type_id
    target_tt = db.query(TreatmentType).filter(TreatmentType.id == target_tt_id).first()
    target_tooth = payload.tooth_number if "tooth_number" in update_data else treatment.tooth_number

    if target_tt:
        if target_tt.category == "general" and target_tooth is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Le soin général '{target_tt.name}' ne peut pas être associé à une dent spécifique (tooth_number doit être NULL)",
            )
        if target_tt.category == "per_tooth" and target_tooth is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Le soin par dent '{target_tt.name}' nécessite un numéro de dent FDI valide (11-48)",
            )

    for field, value in update_data.items():
        setattr(treatment, field, value)

    db.commit()
    db.refresh(treatment)
    return treatment


@treatments_router.delete(
    "/{treatment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a treatment record",
)
def delete_treatment(treatment_id: int, db: Session = Depends(get_db)):
    """Delete a treatment record."""
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment with ID {treatment_id} not found",
        )

    db.delete(treatment)
    db.commit()
    return {"message": f"Treatment #{treatment_id} deleted successfully", "id": treatment_id}
