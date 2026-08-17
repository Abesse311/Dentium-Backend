"""
Phase 6 Verification Test Suite: Dashboard & Settings Module
"""
import os
import sys
from datetime import date
from decimal import Decimal

if sys.platform == "win32" and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi.testclient import TestClient
from backend.database import init_db
from backend.main import app


def test_phase_6():
    print("=" * 60)
    print("  PHASE 6: DASHBOARD & SETTINGS MODULE VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    # 1. Clinic Settings Retrieval & Defaults
    print("\n[1] Testing Clinic Settings Retrieval...")
    res_get_settings = client.get("/api/settings")
    assert res_get_settings.status_code == 200
    settings_data = res_get_settings.json()
    assert settings_data["id"] == 1
    assert settings_data["clinic_name"] is not None
    print(f"  [OK] Retrieved clinic settings: '{settings_data['clinic_name']}' (Limit: {settings_data['daily_patient_limit']}/day)")

    # 2. Clinic Settings Update (PUT / PATCH)
    print("\n[2] Testing Clinic Settings Update...")
    update_payload = {
        "clinic_name": "Clinique Dentaire El Chifa",
        "doctor_name": "Dr. Amina Mansouri",
        "phone": "+213 555 12 34 56",
        "address": "45 Boulevard des Martyrs, Alger",
        "daily_patient_limit": 40,
    }
    res_up_settings = client.put("/api/settings", json=update_payload)
    assert res_up_settings.status_code == 200
    updated_settings = res_up_settings.json()
    assert updated_settings["clinic_name"] == "Clinique Dentaire El Chifa"
    assert updated_settings["doctor_name"] == "Dr. Amina Mansouri"
    assert updated_settings["daily_patient_limit"] == 40
    print("  [OK] Successfully updated clinic info and daily limit to 40")

    # 3. Settings Validation
    print("\n[3] Testing Settings Validation...")
    res_bad_name = client.patch("/api/settings", json={"clinic_name": "   "})
    assert res_bad_name.status_code == 422
    res_bad_limit = client.patch("/api/settings", json={"daily_patient_limit": 0})
    assert res_bad_limit.status_code == 422
    print("  [OK] Rejected invalid clinic_name and limit with 422 Unprocessable Entity")

    # 4. Database Backup Endpoint
    print("\n[4] Testing Database Backup Download Endpoint (/api/settings/backup)...")
    res_backup = client.get("/api/settings/backup")
    assert res_backup.status_code == 200
    assert "application/octet-stream" in res_backup.headers.get("content-type", "")
    assert len(res_backup.content) > 0
    print(f"  [OK] Backup download verified (Received {len(res_backup.content)} bytes)")

    # 5. Dashboard Daily KPIs Setup & Verification
    print("\n[5] Setting up Scenario for Today's Dashboard Metrics...")
    today_str = date.today().isoformat()

    # Create 3 distinct patients for today's tests
    p1 = client.post("/api/patients", json={"full_name": "Nabil Bentaleb", "phone": "0551223344", "birth_date": "1994-11-24"}).json()
    p2 = client.post("/api/patients", json={"full_name": "Adlene Guedioura", "phone": "0551223345", "birth_date": "1985-11-12"}).json()
    p3 = client.post("/api/patients", json={"full_name": "Carl Medjani", "phone": "0551223346", "birth_date": "1985-05-15"}).json()

    # 1 booked appointment for today
    apt1_res = client.post(
        "/api/appointments",
        json={"patient_id": p1["id"], "appointment_date": today_str, "reason": "Contrôle"},
    )
    assert apt1_res.status_code == 201
    apt1_id = apt1_res.json()["id"]

    # 1 completed appointment for today
    apt2_res = client.post(
        "/api/appointments",
        json={"patient_id": p2["id"], "appointment_date": today_str, "reason": "Détartrage"},
    )
    assert apt2_res.status_code == 201
    apt2_id = apt2_res.json()["id"]
    client.patch(f"/api/appointments/{apt2_id}", json={"status": "completed"})

    # 1 no_show appointment for today
    apt3_res = client.post(
        "/api/appointments",
        json={"patient_id": p3["id"], "appointment_date": today_str, "reason": "Consultation"},
    )
    assert apt3_res.status_code == 201
    apt3_id = apt3_res.json()["id"]
    client.patch(f"/api/appointments/{apt3_id}", json={"status": "no_show"})

    # Create an invoice and register a payment made TODAY
    types = client.get("/api/treatment-types").json()
    canal_type = next((t for t in types if t["name"] == "Traitement de canal"), types[0])
    tr_res = client.post(
        "/api/treatments",
        json={"patient_id": p1["id"], "treatment_type_id": canal_type["id"], "status": "completed"},
    )
    tr_id = tr_res.json()["id"]

    inv_res = client.post("/api/invoices", json={"patient_id": p1["id"], "treatment_ids": [tr_id]})
    inv_id = inv_res.json()["id"]

    # Register payment of 8,000 DZD today
    pay_res = client.post(
        f"/api/invoices/{inv_id}/payments",
        json={"amount": 8000.00, "payment_date": today_str, "payment_method": "cash"},
    )
    assert pay_res.status_code == 201

    # Create a planned treatment
    tr_planned_res = client.post(
        "/api/treatments",
        json={"patient_id": p1["id"], "treatment_type_id": canal_type["id"], "status": "planned", "tooth_number": 36},
    )
    assert tr_planned_res.status_code == 201

    # 6. Verify Dashboard Metrics
    print("\n[6] Testing GET /api/dashboard/today...")
    res_dash = client.get("/api/dashboard/today")
    assert res_dash.status_code == 200
    dash_data = res_dash.json()

    assert dash_data["date"] == today_str
    assert dash_data["patients_booked_today"] >= 1
    assert dash_data["patients_completed_today"] >= 1
    assert dash_data["patients_no_show_today"] >= 1
    assert dash_data["total_patients_today"] >= 3
    assert float(dash_data["today_income"]) >= 8000.00
    assert dash_data["pending_treatments_count"] >= 1
    assert dash_data["daily_patient_limit"] >= 1
    assert dash_data["fill_ratio"] > 0
    assert len(dash_data["today_appointments"]) >= 3

    print(f"  [OK] Today's Dashboard Metrics Verified:")
    print(f"        - Booked: {dash_data['patients_booked_today']}")
    print(f"        - Completed: {dash_data['patients_completed_today']}")
    print(f"        - No-Show: {dash_data['patients_no_show_today']}")
    print(f"        - Total Patients: {dash_data['total_patients_today']} / {dash_data['daily_patient_limit']} (Fill Ratio: {dash_data['fill_ratio']})")
    print(f"        - Today's Income: {dash_data['today_income']} DZD")
    print(f"        - Pending Treatments Count: {dash_data['pending_treatments_count']}")
    print(f"        - Today's Agenda Appointments: {len(dash_data['today_appointments'])} items")

    print("\n" + "=" * 60)
    print("  ALL PHASE 6 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_6()
