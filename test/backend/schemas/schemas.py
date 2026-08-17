from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from backend.models.enums import AppointmentStatus, AppointmentType, Gender

# ---------------------------------------------------------------------------
# Medical Notes
# ---------------------------------------------------------------------------

class MedicalNoteBase(BaseModel):
    note: str = Field(
        ...,
        min_length=1,
        description="Clinical observation or diagnosis note.",
        json_schema_extra={"example": "Patient reported sensitivity in upper-left quadrant. Prescribed desensitizing toothpaste."},
    )


class MedicalNoteCreate(MedicalNoteBase):
    patient_id: Optional[int] = None


class MedicalNoteOut(MedicalNoteBase):
    id: int
    patient_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

class AppointmentBase(BaseModel):
    patient_id: int = Field(..., description="ID of the linked patient.")
    appointment_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Date formatted as YYYY-MM-DD.",
        json_schema_extra={"example": "2026-08-15"},
    )
    appointment_time: str = Field(
        ...,
        pattern=r"^\d{2}:\d{2}$",
        description="Time formatted as HH:MM.",
        json_schema_extra={"example": "09:30"},
    )
    appointment_type: str = Field(
        default=AppointmentType.CHECKUP.value,
        description="Type of dental procedure.",
    )
    status: str = Field(
        default=AppointmentStatus.SCHEDULED.value,
        description="Current appointment status.",
    )
    notes: Optional[str] = Field(None, description="Additional appointment notes.")


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    patient_id: Optional[int] = None
    appointment_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    appointment_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    appointment_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AppointmentOut(AppointmentBase):
    id: int
    created_at: datetime
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

class PatientBase(BaseModel):
    full_name: str = Field(
        ...,
        min_length=1,
        description="Full legal name of the patient.",
        json_schema_extra={"example": "Alexander Hayes"},
    )
    phone: Optional[str] = Field(None, description="Contact phone number.")
    birth_date: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format.")
    gender: Optional[str] = Field(None, description="Gender: Male / Female / Other.")
    address: Optional[str] = Field(None, description="Residential address.")
    email: Optional[str] = Field(None, description="Email address.")
    notes: Optional[str] = Field(None, description="General medical background or allergy notes.")


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class PatientOut(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_visit: Optional[str] = None
    appointments_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PatientDetailOut(PatientOut):
    appointments: List[AppointmentOut] = []
    medical_notes: List[MedicalNoteOut] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_patients: int
    today_appointments_count: int
    upcoming_appointments_count: int
    today_patients_count: int
    today_appointments: List[AppointmentOut] = []

    model_config = ConfigDict(from_attributes=True)
