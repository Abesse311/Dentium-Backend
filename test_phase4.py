"""
Phase 4 Verification Test Suite: Treatments Module
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


def test_phase_4():
    print("=" * 60)
    print("  PHASE 4: TREATMENTS MODULE VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    # 1. Treatment Types Catalog
    print("\n[1] Testing Treatment Types Catalog...")
    res_types = client.get("/api/treatment-types")
    assert res_types.status_code == 200
    types = res_types.json()
    assert len(types) >= 7
    print(f"  [OK] Retrieved {len(types)} treatment types from catalog")

    # Add custom treatment type
    res_new_type = client.post(
        "/api/treatment-types",
        json={
            "name": "Pose d'implant en titane",
            "default_price": 60000.00,
            "description": "Implantologie chirurgicale",
        },
    )
    assert res_new_type.status_code == 201
    custom_type = res_new_type.json()
    custom_type_id = custom_type["id"]
    assert custom_type["name"] == "Pose d'implant en titane"
    print(f"  [OK] Added custom treatment type #{custom_type_id}: '{custom_type['name']}' (60,000 DZD)")

    # Update custom treatment type
    res_update_type = client.patch(
        f"/api/treatment-types/{custom_type_id}",
        json={"default_price": 65000.00},
    )
    assert res_update_type.status_code == 200
    assert float(res_update_type.json()["default_price"]) == 65000.00
    print("  [OK] Updated treatment type price to 65,000 DZD")

    # 2. Setup Patient & Appointment for Treatments
    print("\n[2] Setting up Patient & Appointment for Clinical Testing...")
    p_res = client.post("/api/patients", json={"full_name": "Sofiane Feghouli", "phone": "0770334455", "birth_date": "1989-12-26"})
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]

    apt_res = client.post(
        "/api/appointments",
        json={"patient_id": patient_id, "appointment_date": date.today().isoformat(), "reason": "Soins conservateurs"},
    )
    assert apt_res.status_code == 201
    appointment_id = apt_res.json()["id"]
    print(f"  [OK] Created patient #{patient_id} and appointment #{appointment_id}")

    # 3. Create Treatments & Price Fallback
    print("\n[3] Testing Treatment Creation & Automatic Price Fallback...")
    detartrage = next((t for t in types if t["name"] == "Détartrage"), types[0])

    tr_payload1 = {
        "patient_id": patient_id,
        "treatment_type_id": detartrage["id"],
        "appointment_id": appointment_id,
        "tooth_number": None,
        "status": "planned",
        "notes": "Détartrage complet supra-gingival",
    }
    res_tr1 = client.post("/api/treatments", json=tr_payload1)
    assert res_tr1.status_code == 201, f"Create treatment failed: {res_tr1.text}"
    tr1_data = res_tr1.json()
    assert tr1_data["id"] is not None
    assert float(tr1_data["price"]) == float(detartrage["default_price"])
    assert tr1_data["tooth_number"] is None
    assert tr1_data["treatment_type"]["name"] == "Détartrage"
    tr1_id = tr1_data["id"]
    print(f"  [OK] General treatment #{tr1_id} created with auto-applied price {tr1_data['price']} DZD")

    # Create tooth-specific treatment
    plombage = next((t for t in types if t["name"] == "Plombage"), types[1])
    tr_payload2 = {
        "patient_id": patient_id,
        "treatment_type_id": plombage["id"],
        "tooth_number": 26,
        "status": "planned",
        "price": 3500.00,
        "notes": "Carie occlusale profonde dent 26",
    }
    res_tr2 = client.post("/api/treatments", json=tr_payload2)
    assert res_tr2.status_code == 201
    tr2_data = res_tr2.json()
    assert tr2_data["tooth_number"] == 26
    assert float(tr2_data["price"]) == 3500.00
    tr2_id = tr2_data["id"]
    print(f"  [OK] Tooth treatment #{tr2_id} created on FDI tooth #26 with custom price 3,500 DZD")

    # 4. FDI Tooth Notation Validation
    print("\n[4] Testing Tooth Notation Validation (FDI 11-48)...")
    res_bad_tooth = client.post(
        "/api/treatments",
        json={"patient_id": patient_id, "treatment_type_id": detartrage["id"], "tooth_number": 99},
    )
    assert res_bad_tooth.status_code == 422, f"Expected 422 for invalid tooth 99, got {res_bad_tooth.status_code}"
    print("  [OK] Tooth #99 rejected with 422 (must be within FDI range 11-48 or NULL)")

    # 5. Foreign Key Validations
    print("\n[5] Testing Foreign Key Validations...")
    res_no_patient = client.post(
        "/api/treatments",
        json={"patient_id": 999999, "treatment_type_id": detartrage["id"]},
    )
    assert res_no_patient.status_code == 404
    print("  [OK] Non-existent patient_id rejected with 404")

    res_no_tt = client.post(
        "/api/treatments",
        json={"patient_id": patient_id, "treatment_type_id": 999999},
    )
    assert res_no_tt.status_code == 404
    print("  [OK] Non-existent treatment_type_id rejected with 404")

    # 6. Listing and Filters
    print("\n[6] Testing Treatments List & Status Filters...")
    res_planned = client.get("/api/treatments?status=planned")
    assert res_planned.status_code == 200
    planned_list = res_planned.json()
    assert len(planned_list) >= 2
    assert all(t["status"] == "planned" for t in planned_list)
    print(f"  [OK] GET /api/treatments?status=planned returned {len(planned_list)} pending treatment(s)")

    # 7. Update Treatment Status
    print("\n[7] Testing Treatment Status Updates (planned -> in_progress -> completed)...")
    res_prog = client.patch(f"/api/treatments/{tr2_id}", json={"status": "in_progress"})
    assert res_prog.status_code == 200
    assert res_prog.json()["status"] == "in_progress"

    res_comp = client.patch(
        f"/api/treatments/{tr2_id}",
        json={"status": "completed", "notes": "Obturation composite terminée sous digue"},
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "completed"
    print(f"  [OK] Treatment #{tr2_id} transitioned from 'planned' -> 'in_progress' -> 'completed'")

    # 8. Patient Treatment History
    print("\n[8] Testing Patient Odontogram History Endpoint (/api/patients/{id}/treatments)...")
    res_hist = client.get(f"/api/patients/{patient_id}/treatments")
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) == 2
    print(f"  [OK] Patient #{patient_id} treatment history returns {len(history)} records")

    # 9. Delete Treatment
    print("\n[9] Testing Treatment Deletion (DELETE)...")
    res_del_tr = client.delete(f"/api/treatments/{tr1_id}")
    assert res_del_tr.status_code == 200

    res_check_del = client.get(f"/api/treatments/{tr1_id}")
    assert res_check_del.status_code == 404
    print(f"  [OK] Treatment #{tr1_id} deleted successfully")

    # 10. Treatment Type Deletion Protection
    print("\n[10] Testing Treatment Type Deletion Protection...")
    res_del_inuse = client.delete(f"/api/treatment-types/{plombage['id']}")
    assert res_del_inuse.status_code == 400
    print(f"  [OK] Deleting in-use treatment type '{plombage['name']}' properly rejected with 400 Bad Request")

    res_del_unused = client.delete(f"/api/treatment-types/{custom_type_id}")
    assert res_del_unused.status_code == 200
    print(f"  [OK] Deleting unused custom treatment type #{custom_type_id} succeeded")

    print("\n" + "=" * 60)
    print("  ALL PHASE 4 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_4()
