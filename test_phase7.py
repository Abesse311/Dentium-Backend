"""
Phase 7 Verification Test Suite: Financial Analytics & Reporting ("Analyses & Revenus")
"""
import os
import sys
from datetime import date, timedelta
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


def test_phase_7():
    print("=" * 60)
    print("  PHASE 7: FINANCIAL ANALYTICS & REPORTING VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    today = date.today()
    today_str = today.isoformat()

    # 1. Setup Test Patients, Treatments, Invoices & Payments
    print("\n[1] Setting up Clinical & Financial Data for Analytics...")
    p1_res = client.post(
        "/api/patients",
        json={"full_name": "Tariq Ramadan", "phone": "0550123987", "birth_date": "1980-05-15"},
    )
    assert p1_res.status_code == 201
    p1_id = p1_res.json()["id"]

    p2_res = client.post(
        "/api/patients",
        json={"full_name": "Zohra Drif", "phone": "0661987654", "birth_date": "1975-10-20"},
    )
    assert p2_res.status_code == 201
    p2_id = p2_res.json()["id"]

    types = client.get("/api/treatment-types").json()
    detartrage = next((t for t in types if "détartrage" in t["name"].lower()), types[0])
    couronne = next((t for t in types if "couronne" in t["name"].lower()), types[-1])
    extraction = next((t for t in types if "extraction" in t["name"].lower()), types[1])

    # Patient 1: Treatments
    tr1 = client.post(
        "/api/treatments",
        json={"patient_id": p1_id, "treatment_type_id": detartrage["id"], "status": "completed", "price": 4000.00},
    ).json()

    tr2 = client.post(
        "/api/treatments",
        json={"patient_id": p1_id, "treatment_type_id": couronne["id"], "tooth_number": 16, "status": "completed", "price": 16000.00},
    ).json()

    # Patient 2: Treatments
    tr3 = client.post(
        "/api/treatments",
        json={"patient_id": p2_id, "treatment_type_id": extraction["id"], "tooth_number": 28, "status": "completed", "price": 5000.00},
    ).json()

    tr4 = client.post(
        "/api/treatments",
        json={"patient_id": p2_id, "treatment_type_id": couronne["id"], "tooth_number": 26, "status": "completed", "price": 15000.00},
    ).json()

    # Create Invoice 1 for Patient 1: Total 20,000 DZD
    inv1 = client.post(
        "/api/invoices",
        json={"patient_id": p1_id, "treatment_ids": [tr1["id"], tr2["id"]], "invoice_date": today_str},
    ).json()
    inv1_id = inv1["id"]

    # Register partial payment of 8,000 DZD in Cash
    client.post(
        f"/api/invoices/{inv1_id}/payments",
        json={"amount": 8000.00, "payment_date": today_str, "payment_method": "cash", "notes": "Acompte espèces"},
    )

    # Create Invoice 2 for Patient 2: Total 20,000 DZD
    inv2 = client.post(
        "/api/invoices",
        json={"patient_id": p2_id, "treatment_ids": [tr3["id"], tr4["id"]], "invoice_date": today_str},
    ).json()
    inv2_id = inv2["id"]

    # Register full payment of 20,000 DZD by Card
    client.post(
        f"/api/invoices/{inv2_id}/payments",
        json={"amount": 20000.00, "payment_date": today_str, "payment_method": "card", "notes": "Règlement TPE carte"},
    )

    # Create Invoice 3 for Patient 1 (Unpaid): Total 10,000 DZD custom item
    inv3 = client.post(
        "/api/invoices",
        json={
            "patient_id": p1_id,
            "custom_items": [{"description": "Gouttière occlusale spéciale", "amount": 10000.00}],
            "invoice_date": today_str,
        },
    ).json()
    inv3_id = inv3["id"]

    print("  [OK] Test dataset created: 2 patients, 3 invoices (Total: 50,000 DZD, Paid: 28,000 DZD, Debt: 22,000 DZD)")

    # 2. Test Feature 1 & 5: Total Income & Collection Rate (/api/reports/summary)
    print("\n[2] Testing Financial Summary & Collection Rate (/api/reports/summary)...")
    res_summary = client.get("/api/reports/summary?period=today")
    assert res_summary.status_code == 200
    summary = res_summary.json()

    assert summary["period"] == "today"
    assert summary["start_date"] == today_str
    assert summary["end_date"] == today_str
    assert float(summary["total_income"]) >= 28000.00
    assert float(summary["total_invoiced"]) >= 50000.00
    assert 0.0 <= summary["collection_rate"] <= 100.0
    assert float(summary["by_payment_method"]["cash"]) >= 8000.00
    assert float(summary["by_payment_method"]["card"]) >= 20000.00
    assert summary["invoices_summary"]["total_count"] >= 3
    assert summary["invoices_summary"]["paid_count"] >= 1
    assert summary["invoices_summary"]["partially_paid_count"] >= 1
    assert summary["invoices_summary"]["unpaid_count"] >= 1
    print(f"  [OK] Summary computed: Income {summary['total_income']} DZD, Invoiced {summary['total_invoiced']} DZD, Collection Rate {summary['collection_rate']}%")

    # Test period presets
    for p in ["this_week", "this_month", "this_year"]:
        res_p = client.get(f"/api/reports/summary?period={p}")
        assert res_p.status_code == 200
        assert res_p.json()["period"] == p
    print("  [OK] Tested all standard period presets (this_week, this_month, this_year)")

    # Test custom range
    yesterday_str = (today - timedelta(days=1)).isoformat()
    res_custom = client.get(f"/api/reports/summary?start_date={yesterday_str}&end_date={today_str}")
    assert res_custom.status_code == 200
    assert res_custom.json()["period"] == "custom"
    print(f"  [OK] Tested custom date range ({yesterday_str} to {today_str})")

    # 3. Test Feature 2: Income Trend Over Time (/api/reports/trend)
    print("\n[3] Testing Income Trend Over Time (/api/reports/trend)...")
    res_trend_daily = client.get("/api/reports/trend?period=this_month&granularity=daily")
    assert res_trend_daily.status_code == 200
    trend_daily = res_trend_daily.json()
    assert trend_daily["granularity"] == "daily"
    assert len(trend_daily["points"]) >= 28  # Days in month
    today_point = next((pt for pt in trend_daily["points"] if pt["date"] == today_str), None)
    assert today_point is not None
    assert float(today_point["income"]) >= 28000.00
    assert float(today_point["invoiced"]) >= 50000.00
    print(f"  [OK] Daily trend returned {len(trend_daily['points'])} continuous daily points for this month")

    res_trend_monthly = client.get("/api/reports/trend?period=this_year&granularity=monthly")
    assert res_trend_monthly.status_code == 200
    trend_monthly = res_trend_monthly.json()
    assert trend_monthly["granularity"] == "monthly"
    assert len(trend_monthly["points"]) == 12
    print(f"  [OK] Monthly trend returned 12 monthly points for this year")

    # 4. Test Feature 3: Outstanding Debts & Debtor Patients (/api/reports/debts)
    print("\n[4] Testing Outstanding Debts & Debtor Ranking (/api/reports/debts)...")
    res_debts = client.get("/api/reports/debts")
    assert res_debts.status_code == 200
    debts = res_debts.json()

    assert float(debts["total_outstanding_debt"]) >= 22000.00
    assert debts["debtor_patients_count"] >= 1
    assert debts["unpaid_invoices_count"] >= 2
    assert len(debts["debtors"]) >= 1

    # Patient 1 has 12,000 remaining on inv1 + 10,000 on inv3 = 22,000 DZD total debt
    p1_debtor = next((d for d in debts["debtors"] if d["patient_id"] == p1_id), None)
    assert p1_debtor is not None
    assert p1_debtor["patient_name"] == "Tariq Ramadan"
    assert float(p1_debtor["total_debt"]) == 22000.00
    assert p1_debtor["unpaid_invoices_count"] == 2

    # Verify descending sort
    debt_values = [float(d["total_debt"]) for d in debts["debtors"]]
    assert debt_values == sorted(debt_values, reverse=True), "Debtors are not sorted in descending order of debt"
    print(f"  [OK] Debts report verified: Total Debt {debts['total_outstanding_debt']} DZD across {debts['debtor_patients_count']} debtor(s)")

    # 5. Test Feature 4: Revenue Breakdown by Treatment Type (/api/reports/treatments)
    print("\n[5] Testing Revenue Breakdown by Treatment Type (/api/reports/treatments)...")
    res_treatments = client.get("/api/reports/treatments?period=this_month")
    assert res_treatments.status_code == 200
    tr_report = res_treatments.json()

    assert float(tr_report["total_revenue"]) >= 50000.00
    assert len(tr_report["items"]) >= 3

    # Check that Couronne is present (16,000 + 15,000 = 31,000 DZD)
    couronne_item = next((i for i in tr_report["items"] if "couronne" in i["treatment_type_name"].lower()), None)
    assert couronne_item is not None
    assert float(couronne_item["total_amount"]) >= 31000.00
    assert couronne_item["items_count"] >= 2
    assert couronne_item["percentage"] > 0.0

    # Verify percentages are valid
    for item in tr_report["items"]:
        assert 0.0 <= item["percentage"] <= 100.0
    print(f"  [OK] Treatment breakdown verified with {len(tr_report['items'])} procedure types")

    # 6. Test All-in-One Overview Endpoint (/api/reports/overview)
    print("\n[6] Testing All-in-One Overview (/api/reports/overview)...")
    res_overview = client.get("/api/reports/overview?period=this_month")
    assert res_overview.status_code == 200
    overview = res_overview.json()

    assert "summary" in overview
    assert "trend" in overview
    assert "debts" in overview
    assert "treatments" in overview

    assert float(overview["summary"]["total_income"]) >= 28000.00
    assert len(overview["trend"]["points"]) >= 28
    assert len(overview["debts"]["debtors"]) >= 1
    assert len(overview["treatments"]["items"]) >= 3
    print("  [OK] Overview endpoint successfully aggregated all 4 analytical sections in a single payload")

    # 7. Test /api/analytics alias
    print("\n[7] Testing /api/analytics alias endpoints...")
    res_alias = client.get("/api/analytics/summary?period=today")
    assert res_alias.status_code == 200
    assert res_alias.json()["period"] == "today"
    print("  [OK] /api/analytics alias routes verified")

    print("\n" + "=" * 60)
    print("  ALL PHASE 7 TESTS PASSED SUCCESSFULLY! [100% OK]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_phase_7()
