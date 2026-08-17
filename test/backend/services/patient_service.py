from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from backend.models.patient import Patient
from backend.models.appointment import Appointment
from backend.models.medical_note import MedicalNote
from backend.models.enums import AppointmentStatus
from backend.schemas.schemas import PatientCreate, PatientUpdate, PatientOut, PatientDetailOut, AppointmentOut, MedicalNoteOut

class PatientService:
    @staticmethod
    def enrich_patient_out(patient: Patient, db: Session) -> PatientOut:
        # Determine last completed visit
        last_apt = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.status == AppointmentStatus.COMPLETED.value
        ).order_by(desc(Appointment.appointment_date), desc(Appointment.appointment_time)).first()
        
        last_visit = last_apt.appointment_date if last_apt else None
        apt_count = db.query(Appointment).filter(Appointment.patient_id == patient.id).count()

        out = PatientOut.model_validate(patient)
        out.last_visit = last_visit
        out.appointments_count = apt_count
        return out

    @classmethod
    def get_patients(cls, db: Session, search: Optional[str] = None) -> List[PatientOut]:
        query = db.query(Patient)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Patient.full_name.ilike(term),
                    Patient.phone.ilike(term),
                    Patient.email.ilike(term)
                )
            )
        patients = query.order_by(desc(Patient.id)).all()
        return [cls.enrich_patient_out(p, db) for p in patients]

    @classmethod
    def get_patient_detail(cls, db: Session, patient_id: int) -> Optional[PatientDetailOut]:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None

        last_apt = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.status == AppointmentStatus.COMPLETED.value
        ).order_by(desc(Appointment.appointment_date), desc(Appointment.appointment_time)).first()

        out = PatientDetailOut.model_validate(patient)
        out.last_visit = last_apt.appointment_date if last_apt else None
        out.appointments_count = len(patient.appointments)

        # Enriched appointments
        enriched_apts = []
        for apt in sorted(patient.appointments, key=lambda x: (x.appointment_date, x.appointment_time), reverse=True):
            apt_out = AppointmentOut.model_validate(apt)
            apt_out.patient_name = patient.full_name
            apt_out.patient_phone = patient.phone
            enriched_apts.append(apt_out)
        out.appointments = enriched_apts

        # Medical notes
        notes_sorted = sorted(patient.medical_notes, key=lambda x: x.created_at, reverse=True)
        out.medical_notes = [MedicalNoteOut.model_validate(n) for n in notes_sorted]

        return out

    @classmethod
    def create_patient(cls, db: Session, payload: PatientCreate) -> PatientOut:
        patient = Patient(
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            birth_date=payload.birth_date,
            gender=payload.gender,
            address=payload.address.strip() if payload.address else None,
            email=payload.email.strip() if payload.email else None,
            notes=payload.notes.strip() if payload.notes else None
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return cls.enrich_patient_out(patient, db)

    @classmethod
    def update_patient(cls, db: Session, patient_id: int, payload: PatientUpdate) -> Optional[PatientOut]:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None

        update_dict = payload.model_dump(exclude_unset=True)
        if "full_name" in update_dict and update_dict["full_name"]:
            patient.full_name = update_dict["full_name"].strip()

        for key, val in update_dict.items():
            if key != "full_name":
                setattr(patient, key, val.strip() if isinstance(val, str) else val)

        db.commit()
        db.refresh(patient)
        return cls.enrich_patient_out(patient, db)

    @classmethod
    def delete_patient(cls, db: Session, patient_id: int) -> bool:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return False
        db.delete(patient)
        db.commit()
        return True
