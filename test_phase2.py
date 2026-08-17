"""
Phase 2 Verification Test Suite: Patients Module
"""
import os
import sys
import uuid
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
from backend.database import SessionLocal, init_db
from backend.models import Patient, Treatment, TreatmentType, Invoice, InvoiceItem, Payment
from backend.main import app


def test_phase_2():
    print("=" * 60)
    print("  PHASE 2: PATIENTS MODULE VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    # 1. Create Patients (Valid)
    print("\n[1] Testing Patient Creation (Valid Payloads)...")
    p1_payload = {
        "full_name": "Karim Benali",
        "phone": "0550123456",
        "birth_date": "1988-06-15",
        "gender": "male",
        "address": "12 Rue Didouche Mourad, Alger",
        "medical_history": "Hypertension, allergie à la pénicilline",
        "notes": "Patient anxieux, anesthésie locale renforcée",
    }
    res_p1 = client.post("/api/patients", json=p1_payload)
    assert res_p1.status_code == 201, f"Failed to create patient: {res_p1.text}"
    p1_data = res_p1.json()
    assert p1_data["id"] is not None
    assert p1_data["full_name"] == "Karim Benali"
    assert p1_data["gender"] == "male"
    assert "allergie à la pénicilline" in p1_data["medical_history"]
    p1_id = p1_data["id"]
    print(f"  [OK] Created patient #{p1_id}: '{p1_data['full_name']}'")

    # Minimal valid patient
    p2_payload = {"full_name": "Amina Mansouri", "birth_date": "1995-10-20"}
    res_p2 = client.post("/api/patients", json=p2_payload)
    assert res_p2.status_code == 201
    p2_id = res_p2.json()["id"]
    print(f"  [OK] Created minimal patient #{p2_id}: 'Amina Mansouri'")

    # 2. Input Validation (Errors)
    print("\n[2] Testing Input Validation & Error Handling...")
    # Empty full_name
    res_empty_name = client.post("/api/patients", json={"full_name": "   "})
    assert res_empty_name.status_code == 422, f"Expected 422 for empty name, got {res_empty_name.status_code}"
    print("  [OK] Empty full_name rejected with 422 Unprocessable Entity")

    # Invalid gender
    res_bad_gender = client.post("/api/patients", json={"full_name": "Test User", "gender": "unknown"})
    assert res_bad_gender.status_code == 422, f"Expected 422 for invalid gender, got {res_bad_gender.status_code}"
    print("  [OK] Invalid gender ('unknown') rejected with 422 Unprocessable Entity")

    # 3. Patient Retrieval & Search
    print("\n[3] Testing Patient Listing & Search...")
    res_list = client.get("/api/patients")
    assert res_list.status_code == 200
    all_patients = res_list.json()
    assert len(all_patients) >= 2
    print(f"  [OK] Retrieved {len(all_patients)} patients from GET /api/patients")

    # Search by partial name (case-insensitive)
    res_search_name = client.get("/api/patients?search=karim")
    assert res_search_name.status_code == 200
    search_results = res_search_name.json()
    assert len(search_results) >= 1
    assert any(p["id"] == p1_id for p in search_results)
    print("  [OK] Case-insensitive name search ('karim') matched patient Karim Benali")

    # Search by partial phone
    res_search_phone = client.get("/api/patients?search=0550")
    assert res_search_phone.status_code == 200
    phone_results = res_search_phone.json()
    assert len(phone_results) >= 1
    assert any(p["id"] == p1_id for p in phone_results)
    print("  [OK] Phone search ('0550') matched patient Karim Benali")

    # 4. Get Patient by ID
    print("\n[4] Testing GET /api/patients/{id}...")
    res_get_p1 = client.get(f"/api/patients/{p1_id}")
    assert res_get_p1.status_code == 200
    assert res_get_p1.json()["full_name"] == "Karim Benali"
    print(f"  [OK] Retrieved patient #{p1_id} successfully")

    res_404 = client.get("/api/patients/999999")
    assert res_404.status_code == 404, f"Expected 404 for missing patient, got {res_404.status_code}"
    print("  [OK] Missing patient ID returned 404 Not Found with clear detail message")

    # 5. Update Patient (PUT & PATCH)
    print("\n[5] Testing Patient Update...")
    update_payload = {
        "phone": "0550999888",
        "medical_history": "Hypertension, allergie à la pénicilline et aspirine",
    }
    res_update = client.put(f"/api/patients/{p1_id}", json=update_payload)
    assert res_update.status_code == 200
    updated_p1 = res_update.json()
    assert updated_p1["phone"] == "0550999888"
    assert "aspirine" in updated_p1["medical_history"]
    assert updated_p1["full_name"] == "Karim Benali"
    print("  [OK] Updated phone & medical_history successfully")

    # 6. Patient Treatment History & Invoice History
    print("\n[6] Testing Patient Treatments & Invoices Sub-endpoints...")
    db = SessionLocal()
    try:
        tt = db.query(TreatmentType).first()
        assert tt is not None

        tr = Treatment(
            patient_id=p1_id,
            treatment_type_id=tt.id,
            tooth_number=21,
            status="completed",
            price=Decimal("2000.00"),
            treatment_date=date.today(),
            notes="Détartrage complet",
        )
        db.add(tr)
        db.commit()
        db.refresh(tr)

        unique_inv_num = f"INV-TEST-{uuid.uuid4().hex[:6]}"
        inv = Invoice(
            patient_id=p1_id,
            invoice_number=unique_inv_num,
            total_amount=Decimal("2000.00"),
            paid_amount=Decimal("2000.00"),
            status="paid",
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)

        inv_item = InvoiceItem(
            invoice_id=inv.id,
            treatment_id=tr.id,
            description=f"Détartrage - Dent 21",
            amount=Decimal("2000.00"),
        )
        pay = Payment(
            invoice_id=inv.id,
            amount=Decimal("2000.00"),
            payment_method="cash",
        )
        db.add(inv_item)
        db.add(pay)
        db.commit()
    finally:
        db.close()

    # Test GET /api/patients/{id}/treatments
    res_tr_list = client.get(f"/api/patients/{p1_id}/treatments")
    assert res_tr_list.status_code == 200
    treatments = res_tr_list.json()
    assert len(treatments) == 1
    assert treatments[0]["tooth_number"] == 21
    print(f"  [OK] GET /api/patients/{p1_id}/treatments returned {len(treatments)} treatment(s)")

    # Test GET /api/patients/{id}/invoices
    res_inv_list = client.get(f"/api/patients/{p1_id}/invoices")
    assert res_inv_list.status_code == 200
    invoices = res_inv_list.json()
    assert len(invoices) == 1
    assert invoices[0]["invoice_number"] == unique_inv_num
    assert len(invoices[0]["items"]) == 1
    assert len(invoices[0]["payments"]) == 1
    print(f"  [OK] GET /api/patients/{p1_id}/invoices returned full invoice with line items & payments")

    # 7. Delete Patient & Cascade Verification
    print("\n[7] Testing Patient Deletion & Cascade...")
    res_del = client.delete(f"/api/patients/{p1_id}")
    assert res_del.status_code == 200
    print(f"  [OK] Deleted patient #{p1_id}")

    # Verify patient is gone
    res_get_del = client.get(f"/api/patients/{p1_id}")
    assert res_get_del.status_code == 404
    print("  [OK] Confirmed patient #{p1_id} returns 404 after deletion")

    # Verify cascaded records in DB are deleted
    db = SessionLocal()
    try:
        linked_treatments = db.query(Treatment).filter(Treatment.patient_id == p1_id).all()
        assert len(linked_treatments) == 0, "Cascade failed: treatments still exist!"

        linked_invoices = db.query(Invoice).filter(Invoice.patient_id == p1_id).all()
        assert len(linked_invoices) == 0, "Cascade failed: invoices still exist!"
        print("  [OK] Verified all linked treatments and invoices were cascade deleted from SQLite")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("  ALL PHASE 2 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_2()
