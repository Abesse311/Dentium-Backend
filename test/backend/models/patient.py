from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True, index=True)
    birth_date = Column(String(50), nullable=True) # YYYY-MM-DD
    gender = Column(String(20), nullable=True)     # Male / Female / Other
    address = Column(String(255), nullable=True)
    email = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan", order_by="desc(Appointment.appointment_date)")
    medical_notes = relationship("MedicalNote", back_populates="patient", cascade="all, delete-orphan", order_by="desc(MedicalNote.created_at)")
