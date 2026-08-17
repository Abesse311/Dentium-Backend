from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import relationship
from backend.database import Base


class ClinicSettings(Base):
    __tablename__ = "clinic_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_clinic_settings_row"),
    )

    id = Column(Integer, primary_key=True)
    clinic_name = Column(Text, nullable=False, default="Cabinet Dentaire")
    doctor_name = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    logo_path = Column(Text, nullable=True)
    daily_patient_limit = Column(Integer, default=30)


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("gender IN ('male', 'female')", name="chk_patient_gender"),
        Index("idx_patients_name", "full_name"),
        Index("idx_patients_phone", "phone"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(Text, nullable=False)
    phone = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=False)
    gender = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

    # Relationships
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    treatments = relationship("Treatment", back_populates="patient", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="patient", cascade="all, delete-orphan")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("status IN ('booked', 'completed', 'no_show')", name="chk_appointment_status"),
        Index("idx_appointments_date", "appointment_date"),
        Index("idx_appointments_patient", "patient_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    status = Column(Text, default="booked")
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    treatments = relationship("Treatment", back_populates="appointment")


class TreatmentType(Base):
    __tablename__ = "treatment_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    default_price = Column(Numeric(10, 2), default=0.0)
    description = Column(Text, nullable=True)

    # Relationships
    treatments = relationship("Treatment", back_populates="treatment_type")


class Treatment(Base):
    __tablename__ = "treatments"
    __table_args__ = (
        CheckConstraint("status IN ('planned', 'in_progress', 'completed')", name="chk_treatment_status"),
        Index("idx_treatments_patient", "patient_id"),
        Index("idx_treatments_tooth", "patient_id", "tooth_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    treatment_type_id = Column(Integer, ForeignKey("treatment_types.id"), nullable=False)
    tooth_number = Column(Integer, nullable=True)  # FDI notation (11-48), NULL for general
    status = Column(Text, default="planned")
    price = Column(Numeric(10, 2), nullable=False)
    treatment_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

    # Relationships
    patient = relationship("Patient", back_populates="treatments")
    appointment = relationship("Appointment", back_populates="treatments")
    treatment_type = relationship("TreatmentType", back_populates="treatments")
    invoice_items = relationship("InvoiceItem", back_populates="treatment")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("status IN ('unpaid', 'partially_paid', 'paid')", name="chk_invoice_status"),
        Index("idx_invoices_patient", "patient_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(Text, unique=True, nullable=True)
    invoice_date = Column(Date, server_default=func.current_date())
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    status = Column(Text, default="unpaid")
    created_at = Column(DateTime, server_default=func.current_timestamp())

    # Relationships
    patient = relationship("Patient", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("idx_invoice_items_invoice", "invoice_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    treatment_id = Column(Integer, ForeignKey("treatments.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    treatment = relationship("Treatment", back_populates="invoice_items")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("payment_method IN ('cash', 'card', 'transfer', 'other')", name="chk_payment_method"),
        Index("idx_payments_invoice", "invoice_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, server_default=func.current_date())
    payment_method = Column(Text, default="cash")
    notes = Column(Text, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
