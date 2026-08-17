from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# System / Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Clinic Settings
# ---------------------------------------------------------------------------
class ClinicSettingsBase(BaseModel):
    clinic_name: str = Field(default="Cabinet Dentaire", min_length=1)
    doctor_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_path: Optional[str] = None
    daily_patient_limit: int = Field(default=30, ge=1, le=500, description="Configurable daily soft capacity limit")

    @field_validator("clinic_name")
    @classmethod
    def validate_clinic_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("clinic_name cannot be empty or whitespace only")
        return v


class ClinicSettingsUpdate(BaseModel):
    clinic_name: Optional[str] = Field(None, min_length=1)
    doctor_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_path: Optional[str] = None
    daily_patient_limit: Optional[int] = Field(None, ge=1, le=500)

    @field_validator("clinic_name")
    @classmethod
    def validate_clinic_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("clinic_name cannot be empty or whitespace only")
        return v


class ClinicSettingsResponse(BaseModel):
    id: int
    clinic_name: str
    doctor_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_path: Optional[str] = None
    daily_patient_limit: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Treatment Types Catalog
# ---------------------------------------------------------------------------
class TreatmentTypeBase(BaseModel):
    category: Literal["general", "per_tooth"] = Field(
        ...,
        description="Category: 'general' (soin général) or 'per_tooth' (soin par dent)",
    )
    name: str = Field(..., min_length=1, description="French name of the treatment type")
    default_price: Decimal = Field(default=Decimal("0.00"), ge=0, description="Default price in DZD")
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty or whitespace only")
        return v


class TreatmentTypeCreate(TreatmentTypeBase):
    pass


class TreatmentTypeUpdate(BaseModel):
    category: Optional[Literal["general", "per_tooth"]] = None
    name: Optional[str] = Field(None, min_length=1)
    default_price: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("name cannot be empty or whitespace only")
        return v


class TreatmentTypeResponse(BaseModel):
    id: int
    category: str
    name: str
    default_price: Decimal
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Treatments (Odontogram / Dental Records)
# ---------------------------------------------------------------------------
class TreatmentPatientSummary(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TreatmentBase(BaseModel):
    patient_id: int
    treatment_type_id: int
    appointment_id: Optional[int] = None
    tooth_number: Optional[int] = Field(
        None,
        ge=11,
        le=48,
        description="FDI two-digit notation (11-48), NULL for general treatment",
    )
    status: Optional[Literal["planned", "in_progress", "completed"]] = "planned"
    price: Optional[Decimal] = Field(None, ge=0, description="Treatment price in DZD")
    treatment_date: Optional[date] = None
    notes: Optional[str] = None


class TreatmentCreate(TreatmentBase):
    pass


class TreatmentUpdate(BaseModel):
    treatment_type_id: Optional[int] = None
    appointment_id: Optional[int] = None
    tooth_number: Optional[int] = Field(None, ge=11, le=48)
    status: Optional[Literal["planned", "in_progress", "completed"]] = None
    price: Optional[Decimal] = Field(None, ge=0)
    treatment_date: Optional[date] = None
    notes: Optional[str] = None


class TreatmentResponse(BaseModel):
    id: int
    patient_id: int
    appointment_id: Optional[int] = None
    treatment_type_id: int
    tooth_number: Optional[int] = None
    status: str
    price: Decimal
    treatment_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    treatment_type: Optional[TreatmentTypeResponse] = None
    patient: Optional[TreatmentPatientSummary] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Invoices & Payments
# ---------------------------------------------------------------------------
class InvoiceItemBase(BaseModel):
    description: str = Field(..., min_length=1)
    amount: Decimal = Field(..., ge=0)
    treatment_id: Optional[int] = None


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    treatment_id: Optional[int] = None
    description: str
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Payment amount in DZD (must be positive)")
    payment_date: Optional[date] = None
    payment_method: Optional[Literal["cash", "card", "transfer", "other"]] = "cash"
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    payment_date: Optional[date] = None
    payment_method: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InvoicePatientSummary(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    patient_id: int
    treatment_ids: Optional[List[int]] = Field(default=[], description="List of treatment IDs to include in invoice")
    custom_items: Optional[List[InvoiceItemCreate]] = Field(default=[], description="Optional additional line items")
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None


class InvoiceResponse(BaseModel):
    id: int
    patient_id: int
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    total_amount: Decimal
    paid_amount: Decimal
    status: str
    created_at: Optional[datetime] = None
    patient: Optional[InvoicePatientSummary] = None
    items: List[InvoiceItemResponse] = []
    payments: List[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
class PatientBase(BaseModel):
    full_name: str = Field(..., min_length=1, description="Full name of the patient")
    phone: Optional[str] = None
    birth_date: date = Field(..., description="Date of birth of the patient")
    gender: Optional[Literal["male", "female"]] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be empty or whitespace only")
        return v


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[Literal["male", "female"]] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("full_name cannot be empty or whitespace only")
        return v


class PatientResponse(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None
    birth_date: date
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Appointments (Simplified Day-Based Booking)
# ---------------------------------------------------------------------------
class AppointmentPatientSummary(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentBase(BaseModel):
    patient_id: int
    appointment_date: date
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    status: Optional[Literal["booked", "completed", "no_show"]] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    appointment_date: date
    status: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    patient: Optional[AppointmentPatientSummary] = None
    capacity_warning: bool = False

    model_config = ConfigDict(from_attributes=True)


class DayCapacityResponse(BaseModel):
    date: date
    booked_count: int
    limit: int
    fill_ratio: float

    model_config = ConfigDict(from_attributes=True)


class CapacityResponse(BaseModel):
    start_date: date
    end_date: date
    daily_limit: int
    days: List[DayCapacityResponse]


# ---------------------------------------------------------------------------
# Dashboard (Daily Summary & KPIs)
# ---------------------------------------------------------------------------
class DashboardTodayResponse(BaseModel):
    date: date
    patients_booked_today: int
    patients_completed_today: int
    patients_no_show_today: int
    total_patients_today: int
    today_income: Decimal
    pending_treatments_count: int
    daily_patient_limit: int
    fill_ratio: float
    today_appointments: List[AppointmentResponse] = []

    model_config = ConfigDict(from_attributes=True)
