"""
Unified Test Runner for Dental Clinic Backend
Executes all test suites across Phases 1-6.
"""
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from test_phase1 import test_phase_1
from test_phase2 import test_phase_2
from test_phase3 import test_phase_3
from test_phase4 import test_phase_4
from test_phase5 import test_phase_5
from test_phase6 import test_phase_6
from test_phase7 import test_phase_7


def main():
    print("\n" + "#" * 70)
    print("  RUNNING COMPLETE DENTAL CLINIC BACKEND TEST SUITE (PHASES 1-7)")
    print("#" * 70 + "\n")

    phases = [
        ("Phase 1: Project Setup & Database Bootstrap", test_phase_1),
        ("Phase 2: Patients Module", test_phase_2),
        ("Phase 3: Appointments Module (Day-based booking & Capacity)", test_phase_3),
        ("Phase 4: Treatments & Treatment Types Module (Odontogram)", test_phase_4),
        ("Phase 5: Invoices & Payments Module", test_phase_5),
        ("Phase 6: Dashboard & Settings Module", test_phase_6),
        ("Phase 7: Financial Analytics & Reporting ('Analyses & Revenus')", test_phase_7),
    ]

    passed = 0
    for name, test_fn in phases:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            print(f"\n[FAILED] {name}: {exc}")
            raise exc

    print("\n" + "#" * 70)
    print(f"  ALL {passed}/{len(phases)} TEST MODULES PASSED WITH 100% SUCCESS!")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()
