import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import SessionLocal, engine
from backend.models import Patient, Appointment, Treatment, Invoice
from sqlalchemy import func

def cleanup_duplicates():
    db = SessionLocal()
    try:
        # Find duplicate names (case-insensitive)
        duplicates_query = db.query(
            func.lower(Patient.full_name).label("lower_name"),
            func.count(Patient.id).label("count")
        ).group_by(func.lower(Patient.full_name)).having(func.count(Patient.id) > 1).all()
        
        if not duplicates_query:
            print("No duplicate patients found based on name.")
            return

        for dup in duplicates_query:
            lower_name = dup.lower_name
            print(f"\nProcessing duplicates for name: '{lower_name}'")
            
            # Get all patients with this name
            patients = db.query(Patient).filter(func.lower(Patient.full_name) == lower_name).order_by(Patient.id).all()
            
            # Keep the first one (lowest ID)
            kept_patient = patients[0]
            duplicates_to_remove = patients[1:]
            
            print(f"  Keeping patient ID {kept_patient.id} ({kept_patient.full_name})")
            
            for dup_patient in duplicates_to_remove:
                print(f"  Merging & Deleting patient ID {dup_patient.id} ({dup_patient.full_name})")
                
                # 1. Reassign Appointments
                db.query(Appointment).filter(Appointment.patient_id == dup_patient.id).update({"patient_id": kept_patient.id})
                
                # 2. Reassign Treatments
                db.query(Treatment).filter(Treatment.patient_id == dup_patient.id).update({"patient_id": kept_patient.id})
                
                # 3. Reassign Invoices
                db.query(Invoice).filter(Invoice.patient_id == dup_patient.id).update({"patient_id": kept_patient.id})
                
                # 4. Delete the duplicate patient
                db.delete(dup_patient)
                
        db.commit()
        print("\nSuccessfully cleaned up all duplicate patients.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_duplicates()
