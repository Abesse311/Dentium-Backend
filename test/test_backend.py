"""
Automated Backend & SQLite DB Integration Test Suite (English).
"""
import sys
import os

# Set UTF-8 encoding for stdout on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import SessionLocal, engine, Base
from backend.services.seed_data import seed_initial_data
from backend.services.patient_service import PatientService
from backend.services.appointment_service import AppointmentService
from backend.routers import medical_notes
from backend.schemas.schemas import (
    PatientCreate, PatientUpdate, AppointmentCreate, AppointmentUpdate, MedicalNoteCreate
)
from backend.models.enums import AppointmentStatus, AppointmentType, Gender

def run_all_tests():
    print("==================================================")
    print("  RUNNING DENTAL CLINIC BACKEND TEST SUITE")
    print("==================================================")

    # 1. Database Setup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 2. Seed Data Test
        print("\n[TEST 1] Seeding initial English demo data...")
        res = seed_initial_data(db, force=True)
        assert res["status"] == "success"
        print("  -> Seed completed successfully.")

        # 3. Dashboard Statistics Test
        print("\n[TEST 2] Verifying Dashboard Analytics...")
        stats = AppointmentService.get_dashboard_stats(db)
        assert stats.total_patients == 5, f"Expected 5 patients, got {stats.total_patients}"
        assert stats.today_appointments_count >= 3
        print(f"  -> Total Patients: {stats.total_patients}, Today's Appointments: {stats.today_appointments_count}")

        # 4. Patient CRUD Test
        print("\n[TEST 3] Testing Patient CRUD & Search...")
        p_create = PatientCreate(
            full_name="Lucas Sterling",
            phone="+1 (555) 999-0011",
            birth_date="1987-03-22",
            gender=Gender.MALE.value,
            address="500 Tech Blvd, San Francisco, CA",
            email="lucas.sterling@example.com",
            notes="Requires gentle cleaning due to sensitive gums."
        )
        created_p = PatientService.create_patient(db, p_create)
        assert created_p.id is not None
        p_id = created_p.id
        print(f"  -> Created Patient with ID #{p_id}: {created_p.full_name}")

        # Search test
        search_results = PatientService.get_patients(db, search="Lucas")
        assert len(search_results) >= 1
        assert search_results[0].id == p_id
        print("  -> Search by name verified.")

        # Update test
        updated_p = PatientService.update_patient(db, p_id, PatientUpdate(phone="+1 (555) 999-9999"))
        assert updated_p is not None
        assert updated_p.phone == "+1 (555) 999-9999"
        print("  -> Patient update verified.")

        # 5. Clinical Medical Notes Test
        print("\n[TEST 4] Testing Clinical Medical Notes...")
        note_res = medical_notes.create_medical_note(
            p_id,
            MedicalNoteCreate(note="Initial oral assessment: Gingival margin normal, no acute periapical pathology."),
            db
        )
        assert note_res.id is not None
        assert "Initial oral assessment" in note_res.note

        notes_list = medical_notes.get_medical_notes(p_id, db)
        assert len(notes_list) == 1
        print("  -> Medical note creation & retrieval verified.")

        # 6. Appointment CRUD & Flow Test
        print("\n[TEST 5] Testing Appointment Booking & Status Progression...")
        apt_payload = AppointmentCreate(
            patient_id=p_id,
            appointment_date="2026-08-14",
            appointment_time="14:15",
            appointment_type=AppointmentType.CLEANING.value,
            status=AppointmentStatus.SCHEDULED.value,
            notes="Routine 6-month preventive scaling."
        )
        created_apt = AppointmentService.create_appointment(db, apt_payload)
        assert created_apt is not None
        apt_id = created_apt.id
        print(f"  -> Created Appointment #{apt_id} for Patient #{p_id}")

        # Update status to Completed
        updated_apt = AppointmentService.update_appointment(
            db, apt_id, AppointmentUpdate(status=AppointmentStatus.COMPLETED.value)
        )
        assert updated_apt is not None
        assert updated_apt.status == AppointmentStatus.COMPLETED.value
        print("  -> Appointment status changed to 'Completed'.")

        # Check patient detail & last visit date
        patient_chart = PatientService.get_patient_detail(db, p_id)
        assert patient_chart is not None
        assert patient_chart.last_visit == "2026-08-14"
        assert len(patient_chart.appointments) == 1
        assert len(patient_chart.medical_notes) == 1
        print("  -> Patient clinical chart relationships & last_visit calculated properly.")

        # Delete appointment
        del_apt_ok = AppointmentService.delete_appointment(db, apt_id)
        assert del_apt_ok is True
        print("  -> Appointment deleted successfully.")

        # Delete patient
        del_p_ok = PatientService.delete_patient(db, p_id)
        assert del_p_ok is True
        print("  -> Patient and cascaded records deleted successfully.")

        print("\n==================================================")
        print("  ALL BACKEND & SERVICE TESTS PASSED! [100% OK]")
        print("==================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    run_all_tests()
