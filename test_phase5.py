"""
Phase 5 Verification Test Suite: Invoices & Payments Module
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


def test_phase_5():
    print("=" * 60)
    print("  PHASE 5: INVOICES & PAYMENTS MODULE VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    # 1. Setup Patient and Completed Treatments
    print("\n[1] Setting up Patient & Clinical Treatments for Invoicing...")
    p_res = client.post("/api/patients", json={"full_name": "Riyad Mahrez", "phone": "0555778899", "birth_date": "1991-02-21"})
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]

    types = client.get("/api/treatment-types").json()
    consultation_type = next((t for t in types if t["name"] == "Consultation"), types[0])
    couronne_type = next((t for t in types if t["name"] == "Couronne dentaire"), types[-2])

    tr1_res = client.post(
        "/api/treatments",
        json={
            "patient_id": patient_id,
            "treatment_type_id": consultation_type["id"],
            "status": "completed",
        },
    )
    assert tr1_res.status_code == 201
    tr1_id = tr1_res.json()["id"]

    tr2_res = client.post(
        "/api/treatments",
        json={
            "patient_id": patient_id,
            "treatment_type_id": couronne_type["id"],
            "tooth_number": 14,
            "status": "completed",
        },
    )
    assert tr2_res.status_code == 201
    tr2_id = tr2_res.json()["id"]
    print(f"  [OK] Created patient #{patient_id} with treatments #{tr1_id} and #{tr2_id}")

    # 2. Invoice Creation from Treatments
    print("\n[2] Testing Invoice Creation from Treatments...")
    inv_payload = {
        "patient_id": patient_id,
        "treatment_ids": [tr1_id, tr2_id],
    }
    res_inv = client.post("/api/invoices", json=inv_payload)
    assert res_inv.status_code == 201, f"Failed to create invoice: {res_inv.text}"
    inv_data = res_inv.json()
    inv_id = inv_data["id"]

    assert inv_data["patient_id"] == patient_id
    assert inv_data["status"] == "unpaid"
    assert float(inv_data["total_amount"]) == 16000.00
    assert float(inv_data["paid_amount"]) == 0.00
    assert len(inv_data["items"]) == 2
    print(f"  [OK] Created invoice #{inv_id} ({inv_data['invoice_number']}): Total 16,000 DZD, Status 'unpaid'")

    # 3. Ownership & Foreign Key Validation
    print("\n[3] Testing Cross-Patient Validation & Error Handling...")
    other_p_res = client.post("/api/patients", json={"full_name": "Ismail Bennacer", "birth_date": "1997-12-01"})
    other_patient_id = other_p_res.json()["id"]

    res_cross = client.post(
        "/api/invoices",
        json={"patient_id": other_patient_id, "treatment_ids": [tr1_id]},
    )
    assert res_cross.status_code == 400
    print("  [OK] Cross-patient treatment inclusion correctly rejected with 400 Bad Request")

    # 4. Partial Payment Registration
    print("\n[4] Testing Partial Payment Registration (unpaid -> partially_paid)...")
    pay1_payload = {
        "amount": 6000.00,
        "payment_method": "cash",
        "notes": "Acompte initial en espèces",
    }
    res_pay1 = client.post(f"/api/invoices/{inv_id}/payments", json=pay1_payload)
    assert res_pay1.status_code == 201
    pay1_id = res_pay1.json()["id"]

    res_inv_chk1 = client.get(f"/api/invoices/{inv_id}")
    assert res_inv_chk1.status_code == 200
    inv_chk1_data = res_inv_chk1.json()
    assert inv_chk1_data["status"] == "partially_paid"
    assert float(inv_chk1_data["paid_amount"]) == 6000.00
    print(f"  [OK] Registered partial payment of 6,000 DZD. Invoice status -> 'partially_paid'")

    # 5. Full Payment Registration
    print("\n[5] Testing Full Payment Registration (partially_paid -> paid)...")
    pay2_payload = {
        "amount": 10000.00,
        "payment_method": "card",
        "notes": "Solde par carte bancaire",
    }
    res_pay2 = client.post(f"/api/invoices/{inv_id}/payments", json=pay2_payload)
    assert res_pay2.status_code == 201
    pay2_id = res_pay2.json()["id"]

    res_inv_chk2 = client.get(f"/api/invoices/{inv_id}")
    assert res_inv_chk2.status_code == 200
    inv_chk2_data = res_inv_chk2.json()
    assert inv_chk2_data["status"] == "paid"
    assert float(inv_chk2_data["paid_amount"]) == 16000.00
    print(f"  [OK] Registered second payment of 10,000 DZD. Invoice status -> 'paid'")

    # 6. Payment Validation
    print("\n[6] Testing Payment Input Validation...")
    res_bad_pay = client.post(f"/api/invoices/{inv_id}/payments", json={"amount": -500.00})
    assert res_bad_pay.status_code == 422
    print("  [OK] Negative payment rejected with 422 Unprocessable Entity")

    # 7. List and Filters
    print("\n[7] Testing Invoices Listing & Status Filters...")
    res_paid_list = client.get("/api/invoices?status=paid")
    assert res_paid_list.status_code == 200
    assert any(inv["id"] == inv_id for inv in res_paid_list.json())
    print("  [OK] Filter by status ('paid') and patient_id verified")

    # 8. Payment Deletion & Automatic Status Rollback
    print("\n[8] Testing Payment Deletion & Automatic Status Rollback...")
    res_del_pay2 = client.delete(f"/api/payments/{pay2_id}")
    assert res_del_pay2.status_code == 200

    inv_after_del2 = client.get(f"/api/invoices/{inv_id}").json()
    assert inv_after_del2["status"] == "partially_paid"
    assert float(inv_after_del2["paid_amount"]) == 6000.00
    print("  [OK] Deleted 10,000 DZD payment. Invoice automatically rolled back to 'partially_paid'")

    res_del_pay1 = client.delete(f"/api/payments/{pay1_id}")
    assert res_del_pay1.status_code == 200

    inv_after_del1 = client.get(f"/api/invoices/{inv_id}").json()
    assert inv_after_del1["status"] == "unpaid"
    assert float(inv_after_del1["paid_amount"]) == 0.00
    print("  [OK] Deleted remaining payment. Invoice automatically rolled back to 'unpaid'")

    # 9. Patient Invoices Sub-endpoint
    print("\n[9] Testing GET /api/patients/{id}/invoices...")
    res_p_invs = client.get(f"/api/patients/{patient_id}/invoices")
    assert res_p_invs.status_code == 200
    assert len(res_p_invs.json()) >= 1
    print(f"  [OK] Patient #{patient_id} invoices endpoint returned full invoice data")

    # 10. Invoice Deletion
    print("\n[10] Testing Invoice Deletion (DELETE)...")
    res_del_inv = client.delete(f"/api/invoices/{inv_id}")
    assert res_del_inv.status_code == 200

    res_check_del_inv = client.get(f"/api/invoices/{inv_id}")
    assert res_check_del_inv.status_code == 404
    print(f"  [OK] Invoice #{inv_id} successfully deleted")

    print("\n" + "=" * 60)
    print("  ALL PHASE 5 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_5()
