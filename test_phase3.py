"""
Phase 3 Verification Test Suite: Appointments Module
"""
import os
import sys
from datetime import date, timedelta

if sys.platform == "win32" and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi.testclient import TestClient
from backend.database import SessionLocal, init_db
from backend.models import Patient, Appointment, ClinicSettings
from backend.main import app


def test_phase_3():
    print("=" * 60)
    print("  PHASE 3: APPOINTMENTS MODULE VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    # 1. Setup a test patient
    print("\n[1] Creating a test patient for bookings...")
    p_res = client.post("/api/patients", json={"full_name": "Yacine Brahimi", "phone": "0661001122", "birth_date": "1990-02-08"})
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    print(f"  [OK] Test patient created with ID #{patient_id}")

    # 2. Test booking creation (Valid)
    print("\n[2] Testing Day-Based Appointment Creation...")
    target_date = (date.today() + timedelta(days=2)).isoformat()
    apt_payload = {
        "patient_id": patient_id,
        "appointment_date": target_date,
        "reason": "Douleur molaire droite",
        "notes": "Urgence relative",
    }
    res_apt = client.post("/api/appointments", json=apt_payload)
    assert res_apt.status_code == 201, f"Create appointment failed: {res_apt.text}"
    apt_data = res_apt.json()
    assert apt_data["id"] is not None
    assert apt_data["status"] == "booked"
    assert apt_data["appointment_date"] == target_date
    assert apt_data["patient"]["full_name"] == "Yacine Brahimi"
    apt_id = apt_data["id"]
    print(f"  [OK] Created appointment #{apt_id} for date {target_date} (status='booked')")

    # 3. Duplicate appointment prevention on same day (409 Conflict)
    print("\n[3] Testing Duplicate Appointment Prevention on Same Day (409 Conflict)...")
    res_dup = client.post(
        "/api/appointments",
        json={"patient_id": patient_id, "appointment_date": target_date, "reason": "Deuxième rdv même jour"},
    )
    assert res_dup.status_code == 409, f"Expected 409 Conflict for duplicate appointment, got {res_dup.status_code}"
    assert res_dup.json()["detail"] == "Ce patient a déjà un rendez-vous prévu pour cette date."
    print("  [OK] Duplicate appointment on the same date rejected with 409 Conflict")

    # 4. Foreign key validation (Missing patient)
    print("\n[4] Testing Foreign Key Validation (Patient existence)...")
    res_bad_p = client.post("/api/appointments", json={"patient_id": 999999, "appointment_date": target_date})
    assert res_bad_p.status_code == 404, f"Expected 404 for missing patient, got {res_bad_p.status_code}"
    print("  [OK] Non-existent patient_id correctly returned 404 Not Found")

    # 5. Advisory Capacity Limit Test
    print("\n[5] Testing Advisory Capacity Limit & Warning...")
    db = SessionLocal()
    try:
        settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
        old_limit = settings.daily_patient_limit
        settings.daily_patient_limit = 1
        db.commit()
    finally:
        db.close()

    p2_res = client.post("/api/patients", json={"full_name": "Rachid Ghezzal", "birth_date": "1992-05-09"})
    p2_id = p2_res.json()["id"]

    res_cap_warn = client.post(
        "/api/appointments",
        json={"patient_id": p2_id, "appointment_date": target_date, "reason": "Contrôle"},
    )
    assert res_cap_warn.status_code == 201, "Booking should never be blocked by capacity limit!"
    warn_data = res_cap_warn.json()
    assert warn_data["capacity_warning"] is True, f"Expected capacity_warning=True, got {warn_data['capacity_warning']}"
    print("  [OK] Exceeding limit succeeded and correctly returned advisory capacity_warning: true")

    # Restore daily limit
    db = SessionLocal()
    try:
        settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()
        settings.daily_patient_limit = old_limit
        db.commit()
    finally:
        db.close()

    # 6. Capacity Endpoint (/api/appointments/capacity)
    print("\n[6] Testing Capacity & Fill Ratio Endpoint (/api/appointments/capacity)...")
    today_str = date.today().isoformat()
    res_cap = client.get(f"/api/appointments/capacity?start={today_str}&days=7")
    assert res_cap.status_code == 200
    cap_data = res_cap.json()
    assert isinstance(cap_data, list), "Expected capacity endpoint to return a list"
    assert len(cap_data) == 7
    target_day_entry = next((d for d in cap_data if d["date"] == target_date), None)
    assert target_day_entry is not None
    assert target_day_entry["booked_count"] >= 2
    assert "fill_ratio" in target_day_entry
    assert "limit" in target_day_entry
    print(f"  [OK] Capacity endpoint verified for 7 days: {target_date} has {target_day_entry['booked_count']} booked (fill_ratio: {target_day_entry['fill_ratio']})")

    # 7. Week View (/api/appointments/week)
    print("\n[7] Testing Week View Endpoint (/api/appointments/week)...")
    res_week = client.get(f"/api/appointments/week?start={today_str}")
    assert res_week.status_code == 200
    week_apts = res_week.json()
    assert len(week_apts) >= 2
    assert any(a["id"] == apt_id for a in week_apts)
    print(f"  [OK] Week view returned {len(week_apts)} appointment(s) in the 7-day range")

    # 8. List appointments with filters
    print("\n[8] Testing Appointments List & Filters...")
    res_by_date = client.get(f"/api/appointments?date={target_date}")
    assert res_by_date.status_code == 200
    assert len(res_by_date.json()) >= 2

    res_by_patient = client.get(f"/api/appointments?patient_id={patient_id}")
    assert res_by_patient.status_code == 200
    assert len(res_by_patient.json()) >= 1

    res_by_status = client.get("/api/appointments?status=booked")
    assert res_by_status.status_code == 200
    print("  [OK] List filters by date, patient_id, and status verified")

    # 9. Single appointment retrieval
    print("\n[9] Testing GET /api/appointments/{id}...")
    res_get_one = client.get(f"/api/appointments/{apt_id}")
    assert res_get_one.status_code == 200
    assert res_get_one.json()["id"] == apt_id
    assert res_get_one.json()["patient"]["full_name"] == "Yacine Brahimi"

    res_apt_404 = client.get("/api/appointments/999999")
    assert res_apt_404.status_code == 404
    print(f"  [OK] Retrieved appointment #{apt_id} with patient details + 404 checked")

    # 10. Update & Status Transitions (PATCH / PUT)
    print("\n[10] Testing Status Transitions & Rescheduling (PATCH)...")
    res_status_comp = client.patch(f"/api/appointments/{apt_id}", json={"status": "completed"})
    assert res_status_comp.status_code == 200
    assert res_status_comp.json()["status"] == "completed"

    res_resched = client.patch(
        f"/api/appointments/{apt_id}",
        json={"status": "no_show", "notes": "Le patient ne s'est pas présenté"},
    )
    assert res_resched.status_code == 200
    assert res_resched.json()["status"] == "no_show"
    print("  [OK] Status updated to 'completed' and 'no_show'")

    # 11. Cancellation / DELETE
    print("\n[11] Testing Appointment Cancellation (DELETE)...")
    res_del_apt = client.delete(f"/api/appointments/{apt_id}")
    assert res_del_apt.status_code == 200

    res_after_del = client.get(f"/api/appointments/{apt_id}")
    assert res_after_del.status_code == 404
    print(f"  [OK] Appointment #{apt_id} successfully deleted")

    print("\n" + "=" * 60)
    print("  ALL PHASE 3 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_3()
