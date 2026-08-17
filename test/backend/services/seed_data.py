"""
seed_data.py
============
Populates the database with a realistic English demo dataset on first launch,
or when force=True is passed (Settings → Reset Demo Data).
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.appointment import Appointment
from backend.models.medical_note import MedicalNote
from backend.models.enums import AppointmentStatus, AppointmentType, Gender

# ---------------------------------------------------------------------------
# Static demo dataset — easy to extend
# ---------------------------------------------------------------------------

_DEMO_PATIENTS = [
    {
        "full_name": "Alexander Hayes",
        "phone": "+1 (555) 234-5678",
        "birth_date": "1988-04-15",
        "gender": Gender.MALE.value,
        "address": "742 Evergreen Terrace, Springfield",
        "email": "alexander.hayes@example.com",
        "notes": "Mild sensitivity to local anesthesia. Prefers morning visits.",
    },
    {
        "full_name": "Sophia Martinez",
        "phone": "+1 (555) 345-6789",
        "birth_date": "1995-11-20",
        "gender": Gender.FEMALE.value,
        "address": "1204 Elm Street, Austin, TX",
        "email": "sophia.m@example.com",
        "notes": "Undergoing routine preventive care and whitening follow-ups.",
    },
    {
        "full_name": "Marcus Vance",
        "phone": "+1 (555) 456-7890",
        "birth_date": "1982-01-10",
        "gender": Gender.MALE.value,
        "address": "88 Ocean Drive, Miami, FL",
        "email": "marcus.vance@example.com",
        "notes": "Controlled diabetic patient. Monitors blood glucose before major procedures.",
    },
    {
        "full_name": "Emma Watson-Bell",
        "phone": "+1 (555) 567-8901",
        "birth_date": "2001-08-25",
        "gender": Gender.FEMALE.value,
        "address": "55 Maple Avenue, Boston, MA",
        "email": "emma.wb@example.com",
        "notes": "Active orthodontic treatment (ceramic braces).",
    },
    {
        "full_name": "David Chen",
        "phone": "+1 (555) 678-9012",
        "birth_date": "1992-06-05",
        "gender": Gender.MALE.value,
        "address": "310 Pine Street, Seattle, WA",
        "email": "david.chen@example.com",
        "notes": "Minor chip on upper right incisor (#8).",
    },
]

# ---------------------------------------------------------------------------

def _build_appointments(patient_ids: list[int]) -> list[dict]:
    """Return appointment dicts with dynamic dates relative to today."""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    p1, p2, p3, p4, p5 = patient_ids

    return [
        # Today
        dict(patient_id=p1, appointment_date=today,     appointment_time="09:00",
             appointment_type=AppointmentType.CHECKUP.value,   status=AppointmentStatus.SCHEDULED.value,
             notes="Comprehensive oral examination & bitewing X-rays."),
        dict(patient_id=p2, appointment_date=today,     appointment_time="10:30",
             appointment_type=AppointmentType.CLEANING.value,  status=AppointmentStatus.COMPLETED.value,
             notes="Ultrasonic scaling and polishing completed smoothly."),
        dict(patient_id=p3, appointment_date=today,     appointment_time="13:00",
             appointment_type=AppointmentType.ROOT_CANAL.value, status=AppointmentStatus.SCHEDULED.value,
             notes="Second session: canal shaping and obturation on tooth #46."),
        # Tomorrow
        dict(patient_id=p4, appointment_date=tomorrow,  appointment_time="11:00",
             appointment_type=AppointmentType.FOLLOW_UP.value, status=AppointmentStatus.SCHEDULED.value,
             notes="Monthly wire tightening and ligature replacement."),
        # Yesterday
        dict(patient_id=p5, appointment_date=yesterday, appointment_time="15:30",
             appointment_type=AppointmentType.FILLING.value,   status=AppointmentStatus.COMPLETED.value,
             notes="Direct composite restoration on incisor #8 (Shade A2)."),
    ]


def _build_notes(patient_ids: list[int]) -> list[dict]:
    p1, p2, p3, _p4, p5 = patient_ids
    return [
        dict(patient_id=p1, note="Cold sensitivity in upper-left quadrant. No deep caries detected. Prescribed desensitizing toothpaste."),
        dict(patient_id=p2, note="Periodontal probing 2-3 mm throughout. Excellent hygiene. Recommended daily interdental flossing."),
        dict(patient_id=p3, note="Accessed tooth #46. Instrumented MB, ML, and Distal canals without post-op pain."),
        dict(patient_id=p5, note="Composite resin placed with rubber dam isolation. Occlusion adjusted with articulating paper."),
    ]


# ---------------------------------------------------------------------------

def seed_initial_data(db: Session, force: bool = False) -> dict:
    """
    Populate the database with demo data.

    Args:
        db:    SQLAlchemy session.
        force: When True, wipe existing data before seeding.

    Returns:
        A dict with ``status`` and ``message`` keys.
    """
    if db.query(Patient).count() > 0 and not force:
        return {"status": "skipped", "message": "Database already contains data."}

    if force:
        db.query(MedicalNote).delete()
        db.query(Appointment).delete()
        db.query(Patient).delete()
        db.commit()

    # Insert patients
    patient_objs = [Patient(**data) for data in _DEMO_PATIENTS]
    db.add_all(patient_objs)
    db.commit()
    for p in patient_objs:
        db.refresh(p)

    patient_ids = [p.id for p in patient_objs]

    # Insert appointments
    apt_objs = [Appointment(**a) for a in _build_appointments(patient_ids)]
    db.add_all(apt_objs)

    # Insert medical notes
    note_objs = [MedicalNote(**n) for n in _build_notes(patient_ids)]
    db.add_all(note_objs)

    db.commit()
    return {"status": "success", "message": f"Demo data populated: {len(patient_objs)} patients, {len(apt_objs)} appointments."}
