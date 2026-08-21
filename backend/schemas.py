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


VALID_FDI_TEETH = {
    # Quadrant 1 (Upper Right)
    11, 12, 13, 14, 15, 16, 17, 18,
    # Quadrant 2 (Upper Left)
    21, 22, 23, 24, 25, 26, 27, 28,
    # Quadrant 3 (Lower Left)
    31, 32, 33, 34, 35, 36, 37, 38,
    # Quadrant 4 (Lower Right)
    41, 42, 43, 44, 45, 46, 47, 48,
}


class TreatmentBase(BaseModel):
    patient_id: int
    treatment_type_id: int
    appointment_id: Optional[int] = None
    tooth_number: Optional[int] = Field(
        None,
        description="FDI two-digit notation (11-48), NULL for general treatment",
    )
    status: Optional[Literal["planned", "in_progress", "completed"]] = "planned"
    price: Optional[Decimal] = Field(None, ge=0, description="Treatment price in DZD")
    treatment_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("tooth_number")
    @classmethod
    def validate_tooth_number(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in VALID_FDI_TEETH:
            raise ValueError(
                f"Invalid FDI tooth number: {v}. Must be a valid adult FDI tooth notation (11-18, 21-28, 31-38, 41-48)."
            )
        return v


class TreatmentCreate(TreatmentBase):
    pass


class TreatmentBulkCreate(BaseModel):
    patient_id: int
    treatment_type_id: int
    tooth_numbers: List[int] = Field(
        ...,
        min_length=1,
        description="List of FDI two-digit notation tooth numbers (e.g. [18, 28, 38, 48])",
    )
    appointment_id: Optional[int] = None
    status: Optional[Literal["planned", "in_progress", "completed"]] = "planned"
    price: Optional[Decimal] = Field(None, ge=0, description="Treatment price per tooth in DZD")
    treatment_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("tooth_numbers")
    @classmethod
    def validate_tooth_numbers(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("tooth_numbers list cannot be empty")
        
        invalid = [t for t in v if t not in VALID_FDI_TEETH]
        if invalid:
            raise ValueError(f"Invalid FDI tooth number(s): {invalid}. Must be valid adult FDI notation (11-18, 21-28, 31-38, 41-48).")
        
        # Deduplicate while preserving original order
        return list(dict.fromkeys(v))


class TreatmentUpdate(BaseModel):
    treatment_type_id: Optional[int] = None
    appointment_id: Optional[int] = None
    tooth_number: Optional[int] = Field(None, description="FDI two-digit notation (11-48)")
    status: Optional[Literal["planned", "in_progress", "completed"]] = None
    price: Optional[Decimal] = Field(None, ge=0)
    treatment_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("tooth_number")
    @classmethod
    def validate_tooth_number(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in VALID_FDI_TEETH:
            raise ValueError(
                f"Invalid FDI tooth number: {v}. Must be a valid adult FDI tooth notation (11-18, 21-28, 31-38, 41-48)."
            )
        return v


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
    birth_date: Optional[date] = Field(None, description="Date of birth of the patient")
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
    birth_date: Optional[date] = None
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


# ---------------------------------------------------------------------------
# Financial Analytics & Reporting ("Analyses & Revenus")
# ---------------------------------------------------------------------------
class ByPaymentMethod(BaseModel):
    cash: Decimal = Decimal("0.00")
    card: Decimal = Decimal("0.00")
    transfer: Decimal = Decimal("0.00")
    other: Decimal = Decimal("0.00")


class InvoicesSummary(BaseModel):
    total_count: int
    paid_count: int
    partially_paid_count: int
    unpaid_count: int


class ReportSummaryResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    total_income: Decimal
    total_invoiced: Decimal
    collection_rate: float
    payment_count: int
    by_payment_method: ByPaymentMethod
    invoices_summary: InvoicesSummary

    model_config = ConfigDict(from_attributes=True)


class TrendPoint(BaseModel):
    date: str
    label: str
    income: Decimal
    invoiced: Decimal
    payment_count: int


class ReportTrendResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    granularity: str
    points: List[TrendPoint] = []

    model_config = ConfigDict(from_attributes=True)


class DebtorPatient(BaseModel):
    patient_id: int
    patient_name: str
    patient_phone: Optional[str] = None
    total_invoiced: Decimal
    total_paid: Decimal
    total_debt: Decimal
    unpaid_invoices_count: int
    latest_invoice_date: Optional[date] = None


class ReportDebtsResponse(BaseModel):
    total_outstanding_debt: Decimal
    debtor_patients_count: int
    unpaid_invoices_count: int
    debtors: List[DebtorPatient] = []

    model_config = ConfigDict(from_attributes=True)


class TreatmentRevenueItem(BaseModel):
    treatment_type_id: Optional[int] = None
    treatment_type_name: str
    category: Optional[str] = None
    total_amount: Decimal
    items_count: int
    percentage: float


class ReportTreatmentsResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    total_revenue: Decimal
    items: List[TreatmentRevenueItem] = []

    model_config = ConfigDict(from_attributes=True)


class ReportOverviewResponse(BaseModel):
    summary: ReportSummaryResponse
    trend: ReportTrendResponse
    debts: ReportDebtsResponse
    treatments: ReportTreatmentsResponse

    model_config = ConfigDict(from_attributes=True)
