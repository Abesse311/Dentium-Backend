import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH = DATA_DIR / "clinic.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST: str = os.getenv("CLINIC_HOST", "127.0.0.1")
PORT: int = int(os.getenv("CLINIC_PORT", "8000"))
API_BASE_URL: str = f"http://{HOST}:{PORT}"

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME: str = "Dental Clinic Management System"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = (
    "A full-featured desktop practice-management system for dental clinics. "
    "Manages patients, appointments, and clinical records with a real-time FastAPI backend."
)
CONTACT_EMAIL: str = "support@dentalclinic.local"
