import os
from pathlib import Path
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database path: clinic.db in backend directory
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clinic.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Enable foreign keys for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables and seeds default clinic_settings & treatment_types."""
    from backend.models import (
        ClinicSettings,
        TreatmentType,
    )

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed default clinic settings (id=1) if not exists
        settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
        if not settings:
            default_settings = ClinicSettings(
                id=1,
                clinic_name="Cabinet Dentaire",
                doctor_name="Dr. Dentiste",
                phone="",
                address="",
                logo_path=None,
                daily_patient_limit=30,
            )
            db.add(default_settings)

        # Seed treatment types (French catalog) if table is empty
        if db.query(TreatmentType).count() == 0:
            seed_types = [
                TreatmentType(name="Consultation", default_price=Decimal("1000.00"), description="Consultation de routine et diagnostic"),
                TreatmentType(name="Détartrage", default_price=Decimal("2000.00"), description="Nettoyage et détartrage complet"),
                TreatmentType(name="Plombage", default_price=Decimal("3000.00"), description="Obturation dentaire composite/amalgame"),
                TreatmentType(name="Extraction", default_price=Decimal("2500.00"), description="Extraction dentaire simple"),
                TreatmentType(name="Traitement de canal", default_price=Decimal("8000.00"), description="Endodontie / dévitalisation"),
                TreatmentType(name="Couronne dentaire", default_price=Decimal("15000.00"), description="Pose de couronne prothétique"),
                TreatmentType(name="Blanchiment dentaire", default_price=Decimal("6000.00"), description="Éclaircissement dentaire professionnel"),
            ]
            db.add_all(seed_types)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
