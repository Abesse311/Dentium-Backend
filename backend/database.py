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

# Enable foreign keys and WAL mode for SQLite to handle concurrency
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.execute("PRAGMA synchronous = NORMAL")
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
    """Initializes tables and seeds default clinic_settings & treatment_types catalog."""
    from sqlalchemy import text
    from backend.models import (
        ClinicSettings,
        TreatmentType,
    )

    Base.metadata.create_all(bind=engine)

    # Check and migrate existing SQLite tables if 'category' column is missing in treatment_types
    with engine.connect() as conn:
        res = conn.execute(text("PRAGMA table_info(treatment_types)"))
        columns = [row[1] for row in res.fetchall()]
        if columns and "category" not in columns:
            conn.execute(text("ALTER TABLE treatment_types ADD COLUMN category TEXT NOT NULL DEFAULT 'general'"))
            conn.commit()

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

        # Seed full French care catalog (27 types: 14 General + 13 Per-tooth) from catalogue_types_soins.md
        full_catalog = [
            # --- 1) Soins généraux (General) ---
            {"category": "general", "name": "Consultation / Examen général", "default_price": Decimal("1000.00"), "description": "Examen clinique initial du patient"},
            {"category": "general", "name": "Détartrage", "default_price": Decimal("2000.00"), "description": "Nettoyage du tartre dentaire"},
            {"category": "general", "name": "Radiographie panoramique", "default_price": Decimal("2500.00"), "description": "Radio de l'ensemble de la mâchoire"},
            {"category": "general", "name": "Radiographie rétro-alvéolaire", "default_price": Decimal("1000.00"), "description": "Radio localisée"},
            {"category": "general", "name": "Blanchiment dentaire", "default_price": Decimal("15000.00"), "description": "Éclaircissement des dents"},
            {"category": "general", "name": "Orthodontie - début de traitement", "default_price": Decimal("50000.00"), "description": "Pose d'appareil dentaire"},
            {"category": "general", "name": "Contrôle orthodontique", "default_price": Decimal("3000.00"), "description": "Suivi mensuel du traitement"},
            {"category": "general", "name": "Gouttière occlusale / de nuit", "default_price": Decimal("12000.00"), "description": "Protection contre le bruxisme"},
            {"category": "general", "name": "Prothèse complète (dentier)", "default_price": Decimal("35000.00"), "description": "Maxillaire ou mandibulaire"},
            {"category": "general", "name": "Conseil d'hygiène bucco-dentaire", "default_price": Decimal("500.00"), "description": "Éducation du patient"},
            {"category": "general", "name": "Fluoration", "default_price": Decimal("1500.00"), "description": "Application de fluor"},
            {"category": "general", "name": "Anesthésie générale", "default_price": Decimal("10000.00"), "description": "Si disponible au cabinet"},
            {"category": "general", "name": "Chirurgie parodontale générale", "default_price": Decimal("20000.00"), "description": "Traitement des gencives"},
            {"category": "general", "name": "Certificat médical / attestation", "default_price": Decimal("500.00"), "description": "Document administratif"},

            # --- 2) Soins par dent (Per-tooth) ---
            {"category": "per_tooth", "name": "Carie / Obturation (plombage)", "default_price": Decimal("3000.00"), "description": "Composite ou amalgame"},
            {"category": "per_tooth", "name": "Dévitalisation / Traitement de canal", "default_price": Decimal("8000.00"), "description": "Endodontie"},
            {"category": "per_tooth", "name": "Extraction simple", "default_price": Decimal("2500.00"), "description": "Retrait d'une dent"},
            {"category": "per_tooth", "name": "Extraction chirurgicale", "default_price": Decimal("6000.00"), "description": "Extraction complexe"},
            {"category": "per_tooth", "name": "Couronne", "default_price": Decimal("15000.00"), "description": "Métallique, céramique ou zircone"},
            {"category": "per_tooth", "name": "Bridge", "default_price": Decimal("30000.00"), "description": "Nécessite dents piliers"},
            {"category": "per_tooth", "name": "Implant dentaire", "default_price": Decimal("60000.00"), "description": "Pose d'implant"},
            {"category": "per_tooth", "name": "Facette dentaire", "default_price": Decimal("25000.00"), "description": "Céramique ou composite"},
            {"category": "per_tooth", "name": "Scellement de sillons", "default_price": Decimal("2000.00"), "description": "Prévention (enfants)"},
            {"category": "per_tooth", "name": "Pulpotomie / Pulpectomie", "default_price": Decimal("4000.00"), "description": "Dents de lait (enfants)"},
            {"category": "per_tooth", "name": "Reconstruction / Inlay-Onlay", "default_price": Decimal("10000.00"), "description": "Restauration dentaire"},
            {"category": "per_tooth", "name": "Détartrage localisé / surfaçage radiculaire", "default_price": Decimal("3500.00"), "description": "Par dent atteinte"},
            {"category": "per_tooth", "name": "Extraction de dent de sagesse", "default_price": Decimal("7000.00"), "description": "Dent n°18/28/38/48"},
        ]

        existing_types = {t.name.lower(): t for t in db.query(TreatmentType).all()}

        # Seed missing or update existing categories
        for item in full_catalog:
            key = item["name"].lower()
            if key in existing_types:
                # Update category and description if needed
                tt = existing_types[key]
                tt.category = item["category"]
            else:
                new_tt = TreatmentType(
                    category=item["category"],
                    name=item["name"],
                    default_price=item["default_price"],
                    description=item["description"],
                )
                db.add(new_tt)

        # Handle legacy names migration if present
        legacy_mappings = {
            "consultation": ("general", "Consultation / Examen général"),
            "plombage": ("per_tooth", "Carie / Obturation (plombage)"),
            "extraction": ("per_tooth", "Extraction simple"),
            "traitement de canal": ("per_tooth", "Dévitalisation / Traitement de canal"),
            "couronne dentaire": ("per_tooth", "Couronne"),
        }
        for leg_name, (cat, standard_name) in legacy_mappings.items():
            if leg_name in existing_types:
                existing_types[leg_name].category = cat

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
