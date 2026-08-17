from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Appointment, Patient, ClinicSettings
from backend.schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    CapacityResponse,
    DayCapacityResponse,
)

router = APIRouter()


def _get_daily_limit(db: Session) -> int:
    """Helper to fetch the configured daily patient limit from clinic_settings."""
    settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
    if settings and settings.daily_patient_limit:
        return settings.daily_patient_limit
    return 30


@router.get(
    "/capacity",
    response_model=List[DayCapacityResponse],
    summary="Get appointment capacity and fill ratios across a date range",
)
def get_appointment_capacity(
    start: Optional[date] = Query(
        None,
        description="Start date for capacity window (defaults to today)",
    ),
    days: int = Query(7, ge=1, le=60, description="Number of days to check (1 to 60)"),
    db: Session = Depends(get_db),
):
    """Returns daily booked count vs configured capacity limit to assist day-picker fill-ratio color coding."""
    start_date = start or date.today()
    end_date = start_date + timedelta(days=days - 1)
    daily_limit = _get_daily_limit(db)

    # Query appointment counts grouped by date where status != 'cancelled'
    counts_query = (
        db.query(Appointment.appointment_date, func.count(Appointment.id).label("count"))
        .filter(
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date,
            Appointment.status != "cancelled",
        )
        .group_by(Appointment.appointment_date)
        .all()
    )
    counts_map = {row[0]: row[1] for row in counts_query}

    day_list: List[DayCapacityResponse] = []
    current = start_date
    while current <= end_date:
        booked = counts_map.get(current, 0)
        ratio = round(booked / daily_limit, 4) if daily_limit > 0 else 0.0
        day_list.append(
            DayCapacityResponse(
                date=current,
                booked_count=booked,
                limit=daily_limit,
                fill_ratio=ratio,
            )
        )
        current += timedelta(days=1)

    return day_list


@router.get(
    "/week",
    response_model=List[AppointmentResponse],
    summary="List all appointments for a 7-day week window",
)
def get_week_appointments(
    start: Optional[date] = Query(
        None,
        description="Start date of the week (defaults to today)",
    ),
    db: Session = Depends(get_db),
):
    """Retrieve all appointments across a 7-day window starting from given date."""
    start_date = start or date.today()
    end_date = start_date + timedelta(days=6)

    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(Appointment.appointment_date >= start_date)
        .filter(Appointment.appointment_date <= end_date)
        .order_by(Appointment.appointment_date.asc(), Appointment.id.asc())
        .all()
    )
    return appointments


@router.get(
    "",
    response_model=List[AppointmentResponse],
    summary="List appointments filtered by date, patient, or status",
)
def list_appointments(
    appointment_date: Optional[date] = Query(
        None,
        alias="date",
        description="Filter by specific appointment date (YYYY-MM-DD)",
    ),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by appointment status ('booked', 'completed', 'no_show')",
    ),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(200, ge=1, le=1000, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """Retrieve appointments with optional filters for date, patient, or status."""
    query = db.query(Appointment).options(joinedload(Appointment.patient))

    if appointment_date is not None:
        query = query.filter(Appointment.appointment_date == appointment_date)
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)
    if status_filter is not None:
        query = query.filter(Appointment.status == status_filter)

    appointments = (
        query.order_by(Appointment.appointment_date.desc(), Appointment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return appointments


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new day-based appointment booking",
)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    """Create a new day-based booking. Advisory capacity limit warning is returned if day is full, but booking is never blocked."""
    # 1. Validate that the patient exists
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {payload.patient_id} not found",
        )

    # 2. Prevent duplicate active appointments for the same patient on the same day
    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == payload.patient_id,
            Appointment.appointment_date == payload.appointment_date,
            Appointment.status != "cancelled",
        )
        .first()
    )
    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce patient a déjà un rendez-vous prévu pour cette date.",
        )

    # 3. Check capacity advisory limit (excluding cancelled)
    daily_limit = _get_daily_limit(db)
    current_booked = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.appointment_date == payload.appointment_date,
            Appointment.status != "cancelled",
        )
        .scalar()
        or 0
    )
    is_at_or_over_limit = current_booked >= daily_limit

    # 4. Create appointment
    appointment = Appointment(
        patient_id=payload.patient_id,
        appointment_date=payload.appointment_date,
        status="booked",
        reason=payload.reason,
        notes=payload.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # Load patient relation for response
    appointment.patient = patient

    # Attach advisory warning flag
    response = AppointmentResponse.model_validate(appointment)
    response.capacity_warning = is_at_or_over_limit
    return response


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get single appointment details",
)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Retrieve an appointment by ID with patient details."""
    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found",
        )
    return appointment


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update or reschedule an appointment",
)
@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update or reschedule an appointment",
)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
):
    """Update appointment status (booked, completed, no_show), date, reason, or notes."""
    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found",
        )

    # If rescheduling date, ensure no duplicate appointment on the new date
    if payload.appointment_date and payload.appointment_date != appointment.appointment_date:
        existing = (
            db.query(Appointment)
            .filter(
                Appointment.patient_id == appointment.patient_id,
                Appointment.appointment_date == payload.appointment_date,
                Appointment.status != "cancelled",
                Appointment.id != appointment_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce patient a déjà un rendez-vous prévu pour cette date.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel / delete an appointment booking",
)
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Cancel / remove an appointment booking."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found",
        )

    db.delete(appointment)
    db.commit()
    return {"message": f"Appointment #{appointment_id} cancelled successfully", "id": appointment_id}
