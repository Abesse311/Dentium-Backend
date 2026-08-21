import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Invoice, InvoiceItem, Payment, Patient, Treatment, TreatmentType
from backend.schemas import (
    ByPaymentMethod,
    DebtorPatient,
    InvoicesSummary,
    ReportDebtsResponse,
    ReportOverviewResponse,
    ReportSummaryResponse,
    ReportTreatmentsResponse,
    ReportTrendResponse,
    TreatmentRevenueItem,
    TrendPoint,
)

router = APIRouter()

MONTH_NAMES_FR = [
    "Janv.", "Févr.", "Mars", "Avril", "Mai", "Juin",
    "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."
]


def parse_period_range(
    period: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[date, date, str]:
    """
    Parses period parameters ('today', 'this_week', 'this_month', 'this_year', 'custom')
    or explicit date bounds into (start_date, end_date, normalized_period).
    """
    today = date.today()

    if period == "today":
        return today, today, "today"

    if period == "this_week":
        # Monday to Sunday
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end, "this_week"

    if period == "this_month":
        start = date(today.year, today.month, 1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = date(today.year, today.month, last_day)
        return start, end, "this_month"

    if period == "this_year":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
        return start, end, "this_year"

    # Custom or fallback
    if start_date and end_date:
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        return start_date, end_date, "custom"
    elif start_date:
        return start_date, max(start_date, today), "custom"
    elif end_date:
        start = date(end_date.year, end_date.month, 1)
        return start, end_date, "custom"

    # Default to current month if no parameters provided
    start = date(today.year, today.month, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    end = date(today.year, today.month, last_day)
    return start, end, "this_month"


# ---------------------------------------------------------------------------
# Aggregation Helpers
# ---------------------------------------------------------------------------
def compute_summary_report(
    db: Session,
    start_date: date,
    end_date: date,
    period_label: str,
) -> ReportSummaryResponse:
    # 1. Total payments (cash received) in period
    payments = (
        db.query(Payment)
        .filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
        .all()
    )

    total_income = Decimal("0.00")
    by_method_map = {"cash": Decimal("0.00"), "card": Decimal("0.00"), "transfer": Decimal("0.00"), "other": Decimal("0.00")}

    for p in payments:
        p_amount = Decimal(str(p.amount))
        total_income += p_amount
        method_key = (p.payment_method or "cash").lower()
        if method_key in by_method_map:
            by_method_map[method_key] += p_amount
        else:
            by_method_map["other"] += p_amount

    # 2. Total invoiced in period
    invoices = (
        db.query(Invoice)
        .filter(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
        .all()
    )

    total_invoiced = Decimal("0.00")
    paid_count = 0
    partially_paid_count = 0
    unpaid_count = 0

    for inv in invoices:
        total_invoiced += Decimal(str(inv.total_amount))
        status_key = (inv.status or "unpaid").lower()
        if status_key == "paid":
            paid_count += 1
        elif status_key == "partially_paid":
            partially_paid_count += 1
        else:
            unpaid_count += 1

    # 3. Collection Rate
    if total_invoiced > Decimal("0.00"):
        collection_rate = round(float(total_income) / float(total_invoiced) * 100, 2)
    else:
        collection_rate = 100.0 if total_income > Decimal("0.00") else 0.0

    return ReportSummaryResponse(
        period=period_label,
        start_date=start_date,
        end_date=end_date,
        total_income=total_income,
        total_invoiced=total_invoiced,
        collection_rate=collection_rate,
        payment_count=len(payments),
        by_payment_method=ByPaymentMethod(**by_method_map),
        invoices_summary=InvoicesSummary(
            total_count=len(invoices),
            paid_count=paid_count,
            partially_paid_count=partially_paid_count,
            unpaid_count=unpaid_count,
        ),
    )


def compute_trend_report(
    db: Session,
    start_date: date,
    end_date: date,
    period_label: str,
    granularity: Optional[str] = None,
) -> ReportTrendResponse:
    days_span = (end_date - start_date).days + 1
    chosen_granularity = granularity or ("daily" if days_span <= 31 else "monthly")

    points: List[TrendPoint] = []

    if chosen_granularity == "daily":
        # Group payments by date
        payments_query = (
            db.query(
                Payment.payment_date,
                func.sum(Payment.amount).label("sum_amount"),
                func.count(Payment.id).label("count_payments"),
            )
            .filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
            .group_by(Payment.payment_date)
            .all()
        )
        pay_map = {row[0]: (Decimal(str(row[1])), row[2]) for row in payments_query}

        # Group invoices by date
        invoices_query = (
            db.query(
                Invoice.invoice_date,
                func.sum(Invoice.total_amount).label("sum_amount"),
            )
            .filter(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
            .group_by(Invoice.invoice_date)
            .all()
        )
        inv_map = {row[0]: Decimal(str(row[1])) for row in invoices_query}

        curr = start_date
        while curr <= end_date:
            inc, cnt = pay_map.get(curr, (Decimal("0.00"), 0))
            inv = inv_map.get(curr, Decimal("0.00"))
            points.append(
                TrendPoint(
                    date=curr.isoformat(),
                    label=curr.strftime("%d/%m"),
                    income=inc,
                    invoiced=inv,
                    payment_count=cnt,
                )
            )
            curr += timedelta(days=1)

    else:
        # Monthly grouping
        # Determine year-month list
        cur_year, cur_month = start_date.year, start_date.month
        end_year, end_month = end_date.year, end_date.month

        months_list = []
        while (cur_year < end_year) or (cur_year == end_year and cur_month <= end_month):
            months_list.append((cur_year, cur_month))
            if cur_month == 12:
                cur_year += 1
                cur_month = 1
            else:
                cur_month += 1

        payments = (
            db.query(Payment)
            .filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
            .all()
        )
        pay_month_map: Dict[str, Tuple[Decimal, int]] = {}
        for p in payments:
            if p.payment_date:
                k = f"{p.payment_date.year:04d}-{p.payment_date.month:02d}"
                cur_sum, cur_cnt = pay_month_map.get(k, (Decimal("0.00"), 0))
                pay_month_map[k] = (cur_sum + Decimal(str(p.amount)), cur_cnt + 1)

        invoices = (
            db.query(Invoice)
            .filter(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
            .all()
        )
        inv_month_map: Dict[str, Decimal] = {}
        for inv in invoices:
            if inv.invoice_date:
                k = f"{inv.invoice_date.year:04d}-{inv.invoice_date.month:02d}"
                inv_month_map[k] = inv_month_map.get(k, Decimal("0.00")) + Decimal(str(inv.total_amount))

        for y, m in months_list:
            k = f"{y:04d}-{m:02d}"
            label = f"{MONTH_NAMES_FR[m - 1]} {y}"
            inc, cnt = pay_month_map.get(k, (Decimal("0.00"), 0))
            inv = inv_month_map.get(k, Decimal("0.00"))
            points.append(
                TrendPoint(
                    date=k,
                    label=label,
                    income=inc,
                    invoiced=inv,
                    payment_count=cnt,
                )
            )

    return ReportTrendResponse(
        period=period_label,
        start_date=start_date,
        end_date=end_date,
        granularity=chosen_granularity,
        points=points,
    )


def compute_debts_report(db: Session, limit: int = 50) -> ReportDebtsResponse:
    # Query all unpaid or partially paid invoices with patient info
    unpaid_invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.patient))
        .filter(Invoice.status.in_(["unpaid", "partially_paid"]))
        .all()
    )

    total_debt_sum = Decimal("0.00")
    debtor_map: Dict[int, Dict] = {}

    for inv in unpaid_invoices:
        inv_total = Decimal(str(inv.total_amount))
        inv_paid = Decimal(str(inv.paid_amount))
        inv_debt = inv_total - inv_paid
        if inv_debt <= Decimal("0.00"):
            continue

        total_debt_sum += inv_debt

        pid = inv.patient_id
        if pid not in debtor_map:
            p_name = inv.patient.full_name if inv.patient else f"Patient #{pid}"
            p_phone = inv.patient.phone if inv.patient else None
            debtor_map[pid] = {
                "patient_id": pid,
                "patient_name": p_name,
                "patient_phone": p_phone,
                "total_invoiced": Decimal("0.00"),
                "total_paid": Decimal("0.00"),
                "total_debt": Decimal("0.00"),
                "unpaid_invoices_count": 0,
                "latest_invoice_date": inv.invoice_date,
            }

        debtor_map[pid]["total_invoiced"] += inv_total
        debtor_map[pid]["total_paid"] += inv_paid
        debtor_map[pid]["total_debt"] += inv_debt
        debtor_map[pid]["unpaid_invoices_count"] += 1
        if inv.invoice_date and (
            debtor_map[pid]["latest_invoice_date"] is None
            or inv.invoice_date > debtor_map[pid]["latest_invoice_date"]
        ):
            debtor_map[pid]["latest_invoice_date"] = inv.invoice_date

    # Sort debtors descending by total_debt
    sorted_debtors = sorted(
        debtor_map.values(),
        key=lambda x: x["total_debt"],
        reverse=True,
    )

    debtor_items = [DebtorPatient(**d) for d in sorted_debtors[:limit]]

    return ReportDebtsResponse(
        total_outstanding_debt=total_debt_sum,
        debtor_patients_count=len(debtor_map),
        unpaid_invoices_count=len(unpaid_invoices),
        debtors=debtor_items,
    )


def compute_treatments_report(
    db: Session,
    start_date: date,
    end_date: date,
    period_label: str,
) -> ReportTreatmentsResponse:
    # 1. Fetch line items from invoices issued in the period
    invoice_items = (
        db.query(InvoiceItem)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .outerjoin(Treatment, InvoiceItem.treatment_id == Treatment.id)
        .outerjoin(TreatmentType, Treatment.treatment_type_id == TreatmentType.id)
        .options(
            joinedload(InvoiceItem.treatment).joinedload(Treatment.treatment_type),
        )
        .filter(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
        .all()
    )

    total_revenue = Decimal("0.00")
    group_map: Dict[str, Dict] = {}

    for item in invoice_items:
        item_amount = Decimal(str(item.amount))
        total_revenue += item_amount

        tt = item.treatment.treatment_type if (item.treatment and item.treatment.treatment_type) else None
        if tt:
            key = f"tt_{tt.id}"
            tt_id = tt.id
            tt_name = tt.name
            category = tt.category
        else:
            # Custom line item or direct description
            clean_desc = (
                item.description.split("(")[0].strip()
                if (item.description and item.description.split("(")[0].strip())
                else "Prestation diverse"
            )
            key = f"desc_{clean_desc.lower()}"
            tt_id = None
            tt_name = clean_desc
            category = "general"

        if key not in group_map:
            group_map[key] = {
                "treatment_type_id": tt_id,
                "treatment_type_name": tt_name,
                "category": category,
                "total_amount": Decimal("0.00"),
                "items_count": 0,
            }

        group_map[key]["total_amount"] += item_amount
        group_map[key]["items_count"] += 1

    # Sort descending by total_amount
    sorted_items = sorted(
        group_map.values(),
        key=lambda x: x["total_amount"],
        reverse=True,
    )

    items_result: List[TreatmentRevenueItem] = []
    for g in sorted_items:
        pct = (
            round(float(g["total_amount"]) / float(total_revenue) * 100, 2)
            if total_revenue > Decimal("0.00")
            else 0.0
        )
        items_result.append(
            TreatmentRevenueItem(
                treatment_type_id=g["treatment_type_id"],
                treatment_type_name=g["treatment_type_name"],
                category=g["category"],
                total_amount=g["total_amount"],
                items_count=g["items_count"],
                percentage=pct,
            )
        )

    return ReportTreatmentsResponse(
        period=period_label,
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_revenue,
        items=items_result,
    )


# ===========================================================================
# Endpoints
# ===========================================================================
@router.get(
    "/summary",
    response_model=ReportSummaryResponse,
    summary="Total income, invoiced total, and collection rate for a given period",
)
def get_reports_summary(
    period: Optional[Literal["today", "this_week", "this_month", "this_year", "custom"]] = Query(
        None,
        description="Period preset: 'today', 'this_week', 'this_month', 'this_year', or 'custom'",
    ),
    start_date: Optional[date] = Query(None, description="Start date (inclusive) for custom period"),
    end_date: Optional[date] = Query(None, description="End date (inclusive) for custom period"),
    db: Session = Depends(get_db),
):
    """Compute financial summary (income, billed, collection rate, payment methods) for a period."""
    start_d, end_d, norm_period = parse_period_range(period, start_date, end_date)
    return compute_summary_report(db, start_d, end_d, norm_period)


@router.get(
    "/trend",
    response_model=ReportTrendResponse,
    summary="Income and billing trend over time",
)
def get_reports_trend(
    period: Optional[Literal["today", "this_week", "this_month", "this_year", "custom"]] = Query(
        None,
        description="Period preset: 'today', 'this_week', 'this_month', 'this_year', or 'custom'",
    ),
    start_date: Optional[date] = Query(None, description="Start date (inclusive) for custom period"),
    end_date: Optional[date] = Query(None, description="End date (inclusive) for custom period"),
    granularity: Optional[Literal["daily", "monthly"]] = Query(
        None,
        description="Bucket granularity ('daily' or 'monthly'). Auto-detected if omitted.",
    ),
    db: Session = Depends(get_db),
):
    """Retrieve time-series trend data points for rendering income evolution charts."""
    start_d, end_d, norm_period = parse_period_range(period, start_date, end_date)
    return compute_trend_report(db, start_d, end_d, norm_period, granularity)


@router.get(
    "/debts",
    response_model=ReportDebtsResponse,
    summary="Outstanding debts (créances) and debtor patient ranking",
)
def get_reports_debts(
    limit: int = Query(50, ge=1, le=500, description="Max debtor patients to return"),
    db: Session = Depends(get_db),
):
    """Retrieve total outstanding balances across all invoices and list of debtor patients sorted by debt."""
    return compute_debts_report(db, limit=limit)


@router.get(
    "/treatments",
    response_model=ReportTreatmentsResponse,
    summary="Revenue breakdown by treatment type",
)
def get_reports_treatments(
    period: Optional[Literal["today", "this_week", "this_month", "this_year", "custom"]] = Query(
        None,
        description="Period preset: 'today', 'this_week', 'this_month', 'this_year', or 'custom'",
    ),
    start_date: Optional[date] = Query(None, description="Start date (inclusive) for custom period"),
    end_date: Optional[date] = Query(None, description="End date (inclusive) for custom period"),
    db: Session = Depends(get_db),
):
    """Compute revenue and frequency distribution grouped by dental treatment type."""
    start_d, end_d, norm_period = parse_period_range(period, start_date, end_date)
    return compute_treatments_report(db, start_d, end_d, norm_period)


@router.get(
    "/overview",
    response_model=ReportOverviewResponse,
    summary="Comprehensive financial analytics overview for the 'Analyses & Revenus' page",
)
def get_reports_overview(
    period: Optional[Literal["today", "this_week", "this_month", "this_year", "custom"]] = Query(
        None,
        description="Period preset: 'today', 'this_week', 'this_month', 'this_year', or 'custom'",
    ),
    start_date: Optional[date] = Query(None, description="Start date (inclusive) for custom period"),
    end_date: Optional[date] = Query(None, description="End date (inclusive) for custom period"),
    granularity: Optional[Literal["daily", "monthly"]] = Query(
        None,
        description="Bucket granularity for trend ('daily' or 'monthly')",
    ),
    debts_limit: int = Query(10, ge=1, le=100, description="Top debtor patients count in overview"),
    db: Session = Depends(get_db),
):
    """Retrieve complete analytics dataset (summary, trend, debts, treatment breakdown) in a single request."""
    start_d, end_d, norm_period = parse_period_range(period, start_date, end_date)

    summary_data = compute_summary_report(db, start_d, end_d, norm_period)
    trend_data = compute_trend_report(db, start_d, end_d, norm_period, granularity)
    debts_data = compute_debts_report(db, limit=debts_limit)
    treatments_data = compute_treatments_report(db, start_d, end_d, norm_period)

    return ReportOverviewResponse(
        summary=summary_data,
        trend=trend_data,
        debts=debts_data,
        treatments=treatments_data,
    )
