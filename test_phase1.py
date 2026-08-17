"""
Phase 1 Verification Test Suite
"""
import os
import sys
import io

if sys.platform == "win32" and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from decimal import Decimal
from sqlalchemy import inspect, text
from fastapi.testclient import TestClient

from backend.database import engine, SessionLocal, init_db, DB_PATH
from backend.models import (
    ClinicSettings,
    Patient,
    Appointment,
    TreatmentType,
    Treatment,
    Invoice,
    InvoiceItem,
    Payment,
)
from backend.main import app


def test_phase_1():
    print("=" * 60)
    print("  PHASE 1: PROJECT SETUP & DATABASE VERIFICATION")
    print("=" * 60)

    # 1. Initialize database
    print("\n[1] Initializing SQLite database...")
    init_db()
    assert os.path.exists(DB_PATH), f"Database file not found at {DB_PATH}"
    print(f"  [OK] Database file verified at: {DB_PATH}")

    # 2. Verify all 8 tables exist
    print("\n[2] Verifying tables in database schema...")
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = {
        "clinic_settings",
        "patients",
        "appointments",
        "treatment_types",
        "treatments",
        "invoices",
        "invoice_items",
        "payments",
    }

    missing = expected_tables - existing_tables
    assert not missing, f"Missing tables in schema: {missing}"
    print(f"  [OK] All {len(expected_tables)} tables exist:")
    for t in sorted(existing_tables):
        print(f"        - {t}")

    # 3. Check SQLite PRAGMA foreign_keys
    print("\n[3] Verifying SQLite PRAGMA foreign_keys is ON...")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        assert result == 1, f"PRAGMA foreign_keys expected 1, got {result}"
    print("  [OK] PRAGMA foreign_keys = 1 (ON)")

    # 4. Verify seed data
    print("\n[4] Verifying Seed Data...")
    db = SessionLocal()
    try:
        # Check clinic_settings
        settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
        assert settings is not None, "clinic_settings id=1 row missing!"
        assert settings.daily_patient_limit >= 1
        print(f"  [OK] Default clinic settings verified: '{settings.clinic_name}' (Limit: {settings.daily_patient_limit}/day)")

        # Check treatment_types
        types = db.query(TreatmentType).all()
        assert len(types) >= 7
        expected_type_names = {
            "Consultation",
            "Détartrage",
            "Plombage",
            "Extraction",
            "Traitement de canal",
            "Couronne dentaire",
            "Blanchiment dentaire",
        }
        actual_type_names = {t.name for t in types}
        assert expected_type_names.issubset(actual_type_names)
        print(f"  [OK] French Treatment Types verified:")
        for t in types[:7]:
            print(f"        - {t.name}: {t.default_price} DZD")
    finally:
        db.close()

    # 5. Verify FastAPI endpoints & CORS
    print("\n[5] Verifying FastAPI Endpoints & CORS Middleware...")
    with TestClient(app) as client:
        # Root endpoint
        res_root = client.get("/")
        assert res_root.status_code == 200, f"Root returned status {res_root.status_code}"
        print(f"  [OK] GET / -> {res_root.json()}")

        # Health check
        res_health = client.get("/api/health")
        assert res_health.status_code == 200, f"Health check failed with {res_health.status_code}"
        data = res_health.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        print(f"  [OK] GET /api/health -> {data}")

        # CORS check on GET with Origin
        res_cors_get = client.get("/api/health", headers={"origin": "http://localhost:3000"})
        origin_header = res_cors_get.headers.get("access-control-allow-origin")
        assert origin_header in ("*", "http://localhost:3000"), f"CORS header invalid: {origin_header}"
        assert res_cors_get.headers.get("access-control-allow-credentials") == "true"
        print("  [OK] CORS headers on GET verified (echoes origin + credentials allowed)")

        # CORS preflight OPTIONS
        res_cors_opt = client.options(
            "/api/health",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "GET",
            },
        )
        opt_origin_header = res_cors_opt.headers.get("access-control-allow-origin")
        assert opt_origin_header in ("*", "http://localhost:3000"), f"Preflight CORS failed: {opt_origin_header}"
        assert res_cors_opt.headers.get("access-control-allow-credentials") == "true"
        print("  [OK] CORS preflight OPTIONS verified (echoes origin + credentials allowed)")

    print("\n" + "=" * 60)
    print("  ALL PHASE 1 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_1()
