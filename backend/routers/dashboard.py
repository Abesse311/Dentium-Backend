from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Appointment, Payment, Treatment, ClinicSettings
from backend.schemas import DashboardTodayResponse

router = APIRouter()


@router.get(
    "/today",
    response_model=DashboardTodayResponse,
    summary="Get at-a-glance daily dashboard statistics",
)
@router.get(
    "/stats",
    response_model=DashboardTodayResponse,
    summary="Get at-a-glance daily dashboard statistics",
    include_in_schema=False,
)
def get_dashboard_today(
    target_date: Optional[date] = Query(
        None,
        alias="date",
        description="Date to compute metrics for (defaults to today)",
    ),
    db: Session = Depends(get_db),
):
    """Retrieve live operational KPIs for today: bookings, completions, no-shows, revenue, and pending treatments."""
    eval_date = target_date or date.today()

    # 1. Fetch clinic daily patient limit dynamically
    settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
    daily_limit = settings.daily_patient_limit if (settings and settings.daily_patient_limit) else 30

    # 2. Query today's active appointments (excluding cancelled)
    today_appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.appointment_date == eval_date,
            Appointment.status != "cancelled",
        )
        .order_by(Appointment.status.asc(), Appointment.id.asc())
        .all()
    )

    booked_count = sum(1 for a in today_appointments if a.status == "booked")
    completed_count = sum(1 for a in today_appointments if a.status == "completed")
    no_show_count = sum(1 for a in today_appointments if a.status == "no_show")
    total_today = len(today_appointments)

    fill_ratio = round(total_today / daily_limit, 4) if daily_limit > 0 else 0.0

    # 3. Live sum of payments received today (from payments table where payment_date == eval_date)
    today_income_sum = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.payment_date == eval_date)
        .scalar()
        or Decimal("0.00")
    )
    today_income = Decimal(str(today_income_sum))

    # 4. Live count of treatments with status in ['planned', 'in_progress']
    pending_treatments_count = (
        db.query(func.count(Treatment.id))
        .filter(Treatment.status.in_(["planned", "in_progress"]))
        .scalar()
        or 0
    )

    return DashboardTodayResponse(
        date=eval_date,
        patients_booked_today=booked_count,
        patients_completed_today=completed_count,
        patients_no_show_today=no_show_count,
        total_patients_today=total_today,
        today_income=today_income,
        pending_treatments_count=pending_treatments_count,
        daily_patient_limit=daily_limit,
        fill_ratio=fill_ratio,
        today_appointments=today_appointments,
    )
