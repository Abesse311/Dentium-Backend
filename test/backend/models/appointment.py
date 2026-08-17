from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
from backend.models.enums import AppointmentStatus, AppointmentType

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_date = Column(String(50), nullable=False, index=True) # YYYY-MM-DD
    appointment_time = Column(String(50), nullable=False)             # HH:MM
    appointment_type = Column(String(100), nullable=False, default=AppointmentType.CHECKUP.value)
    status = Column(String(50), nullable=False, default=AppointmentStatus.SCHEDULED.value)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
