from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from backend.models.appointment import Appointment
from backend.models.patient import Patient
from backend.models.enums import AppointmentStatus, AppointmentType
from backend.schemas.schemas import AppointmentCreate, AppointmentUpdate, AppointmentOut, DashboardStats

class AppointmentService:
    @staticmethod
    def enrich_appointment_out(apt: Appointment) -> AppointmentOut:
        out = AppointmentOut.model_validate(apt)
        if apt.patient:
            out.patient_name = apt.patient.full_name
            out.patient_phone = apt.patient.phone
        return out

    @classmethod
    def get_appointments(
        cls,
        db: Session,
        date_str: Optional[str] = None,
        patient_id: Optional[int] = None,
        status_val: Optional[str] = None,
        type_val: Optional[str] = None
    ) -> List[AppointmentOut]:
        query = db.query(Appointment)
        if date_str:
            query = query.filter(Appointment.appointment_date == date_str)
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if status_val:
            query = query.filter(Appointment.status == status_val)
        if type_val:
            query = query.filter(Appointment.appointment_type == type_val)

        appointments = query.order_by(
            desc(Appointment.appointment_date),
            Appointment.appointment_time
        ).all()

        return [cls.enrich_appointment_out(a) for a in appointments]

    @classmethod
    def get_today_appointments(cls, db: Session) -> List[AppointmentOut]:
        today_str = date.today().isoformat()
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date == today_str
        ).order_by(Appointment.appointment_time).all()

        return [cls.enrich_appointment_out(a) for a in appointments]

    @classmethod
    def get_appointment(cls, db: Session, appointment_id: int) -> Optional[AppointmentOut]:
        apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not apt:
            return None
        return cls.enrich_appointment_out(apt)

    @classmethod
    def create_appointment(cls, db: Session, payload: AppointmentCreate) -> Optional[AppointmentOut]:
        # Ensure patient exists
        patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
        if not patient:
            return None

        apt = Appointment(
            patient_id=payload.patient_id,
            appointment_date=payload.appointment_date.strip(),
            appointment_time=payload.appointment_time.strip(),
            appointment_type=payload.appointment_type.strip() if payload.appointment_type else AppointmentType.CHECKUP.value,
            status=payload.status.strip() if payload.status else AppointmentStatus.SCHEDULED.value,
            notes=payload.notes.strip() if payload.notes else None
        )
        db.add(apt)
        db.commit()
        db.refresh(apt)
        return cls.enrich_appointment_out(apt)

    @classmethod
    def update_appointment(cls, db: Session, appointment_id: int, payload: AppointmentUpdate) -> Optional[AppointmentOut]:
        apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not apt:
            return None

        update_dict = payload.model_dump(exclude_unset=True)
        if "patient_id" in update_dict and update_dict["patient_id"] is not None:
            patient = db.query(Patient).filter(Patient.id == update_dict["patient_id"]).first()
            if not patient:
                return None
            apt.patient_id = update_dict["patient_id"]

        for key, val in update_dict.items():
            if key != "patient_id":
                setattr(apt, key, val.strip() if isinstance(val, str) else val)

        db.commit()
        db.refresh(apt)
        return cls.enrich_appointment_out(apt)

    @classmethod
    def delete_appointment(cls, db: Session, appointment_id: int) -> bool:
        apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not apt:
            return False
        db.delete(apt)
        db.commit()
        return True

    @classmethod
    def get_dashboard_stats(cls, db: Session) -> DashboardStats:
        today_str = date.today().isoformat()

        total_patients = db.query(func.count(Patient.id)).scalar() or 0

        today_appointments = db.query(Appointment).filter(
            Appointment.appointment_date == today_str
        ).order_by(Appointment.appointment_time).all()

        today_count = len(today_appointments)

        today_patients_count = db.query(func.count(func.distinct(Appointment.patient_id))).filter(
            Appointment.appointment_date == today_str
        ).scalar() or 0

        upcoming_count = db.query(func.count(Appointment.id)).filter(
            Appointment.appointment_date >= today_str,
            Appointment.status == AppointmentStatus.SCHEDULED.value
        ).scalar() or 0

        return DashboardStats(
            total_patients=total_patients,
            today_appointments_count=today_count,
            upcoming_appointments_count=upcoming_count,
            today_patients_count=today_patients_count,
            today_appointments=[cls.enrich_appointment_out(a) for a in today_appointments]
        )
