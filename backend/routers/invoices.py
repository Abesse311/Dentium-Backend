from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Invoice, InvoiceItem, Payment, Patient, Treatment, ClinicSettings
from backend.schemas import (
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
)
from backend.services.pdf_service import generate_invoice_pdf

invoices_router = APIRouter()
payments_router = APIRouter()


def _recalculate_invoice_status(invoice: Invoice, db: Session) -> None:
    """Helper to recalculate paid_amount and status (unpaid, partially_paid, paid) based on linked payments."""
    total_paid = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.invoice_id == invoice.id)
        .scalar()
        or Decimal("0.00")
    )
    invoice.paid_amount = Decimal(str(total_paid))

    if invoice.paid_amount <= Decimal("0.00"):
        invoice.status = "unpaid"
    elif invoice.paid_amount < invoice.total_amount:
        invoice.status = "partially_paid"
    else:
        invoice.status = "paid"


# ===========================================================================
# 1. Invoices Endpoints (/api/invoices)
# ===========================================================================
@invoices_router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an invoice from treatments and/or custom items",
)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice. Can pull one or more completed treatments to generate line items automatically."""
    # 1. Validate patient existence
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {payload.patient_id} not found",
        )

    # 2. Build invoice line items
    items_to_create: List[InvoiceItem] = []
    total_amount = Decimal("0.00")

    # Pull treatments
    if payload.treatment_ids:
        treatments = (
            db.query(Treatment)
            .options(joinedload(Treatment.treatment_type))
            .filter(Treatment.id.in_(payload.treatment_ids))
            .all()
        )
        found_ids = {t.id for t in treatments}
        missing_ids = set(payload.treatment_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Treatment ID(s) not found: {sorted(list(missing_ids))}",
            )

        for tr in treatments:
            if tr.patient_id != payload.patient_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Treatment #{tr.id} belongs to patient #{tr.patient_id}, not patient #{payload.patient_id}",
                )

            type_name = tr.treatment_type.name if tr.treatment_type else "Traitement"
            tooth_suffix = f" (Dent {tr.tooth_number})" if tr.tooth_number else ""
            desc = f"{type_name}{tooth_suffix}"
            item_price = Decimal(str(tr.price))

            item = InvoiceItem(
                treatment_id=tr.id,
                description=desc,
                amount=item_price,
            )
            items_to_create.append(item)
            total_amount += item_price

    # Pull custom items
    if payload.custom_items:
        for ci in payload.custom_items:
            c_amount = Decimal(str(ci.amount))
            item = InvoiceItem(
                treatment_id=ci.treatment_id,
                description=ci.description,
                amount=c_amount,
            )
            items_to_create.append(item)
            total_amount += c_amount

    # 3. Generate sequential invoice number if omitted
    inv_date = payload.invoice_date or date.today()
    if payload.invoice_number:
        inv_number = payload.invoice_number.strip()
    else:
        current_year = inv_date.year
        existing_numbers = (
            db.query(Invoice.invoice_number)
            .filter(
                (Invoice.invoice_number.like(f"FAC-{current_year}-%"))
                | (Invoice.invoice_number.like(f"INV-{current_year}-%"))
            )
            .all()
        )
        max_seq = 0
        for (num_str,) in existing_numbers:
            if num_str:
                parts = num_str.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    seq = int(parts[-1])
                    if seq > max_seq:
                        max_seq = seq

        inv_number = f"FAC-{current_year}-{(max_seq + 1):04d}"

    # 4. Create Invoice
    invoice = Invoice(
        patient_id=payload.patient_id,
        invoice_number=inv_number,
        invoice_date=inv_date,
        total_amount=total_amount,
        paid_amount=Decimal("0.00"),
        status="unpaid",
    )
    db.add(invoice)
    db.flush()  # Populates invoice.id

    for item in items_to_create:
        item.invoice_id = invoice.id
        db.add(item)

    db.commit()
    db.refresh(invoice)

    invoice.patient = patient
    invoice.items = items_to_create
    invoice.payments = []
    return invoice


@invoices_router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="List invoices with optional filters",
)
def list_invoices(
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by invoice status: 'unpaid', 'partially_paid', 'paid'",
    ),
    date_filter: Optional[date] = Query(None, alias="date", description="Filter invoices for an exact single date (YYYY-MM-DD)"),
    date_from: Optional[date] = Query(None, description="Filter invoices from date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter invoices to date (inclusive)"),
    start_date: Optional[date] = Query(None, description="Alias for date_from"),
    end_date: Optional[date] = Query(None, description="Alias for date_to"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(200, ge=1, le=1000, description="Max invoices to return"),
    db: Session = Depends(get_db),
):
    """List invoices with items, payments, and patient summary."""
    query = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.patient),
            joinedload(Invoice.items),
            joinedload(Invoice.payments),
        )
    )

    effective_from = date_from or start_date
    effective_to = date_to or end_date

    if patient_id is not None:
        query = query.filter(Invoice.patient_id == patient_id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if date_filter is not None:
        query = query.filter(Invoice.invoice_date == date_filter)
    if effective_from is not None:
        query = query.filter(Invoice.invoice_date >= effective_from)
    if effective_to is not None:
        query = query.filter(Invoice.invoice_date <= effective_to)

    invoices = (
        query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return invoices


@invoices_router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice details by ID",
)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of an invoice, including line items and registered payments."""
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.patient),
            joinedload(Invoice.items),
            joinedload(Invoice.payments),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )
    return invoice


@invoices_router.get(
    "/{invoice_id}/pdf",
    summary="Export and download invoice as PDF",
    response_description="Returns the generated PDF file",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Invoice PDF document",
        },
        404: {"description": "Invoice not found"},
    },
)
def get_invoice_pdf(invoice_id: int, db: Session = Depends(get_db)):
    """Generate and return a downloadable PDF for any invoice (unpaid, partially paid, or paid)."""
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.patient),
            joinedload(Invoice.items),
            joinedload(Invoice.payments),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )

    clinic_settings = db.query(ClinicSettings).filter(ClinicSettings.id == 1).first()

    pdf_bytes = generate_invoice_pdf(invoice=invoice, settings=clinic_settings)
    filename = f"facture_{invoice.invoice_number or f'FAC-{invoice_id:04d}'}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@invoices_router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an invoice",
)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Delete an invoice and its line items and payments."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )

    db.delete(invoice)
    db.commit()
    return {"message": f"Invoice #{invoice_id} deleted successfully", "id": invoice_id}


# ===========================================================================
# 2. Payments Endpoints (/api/invoices/{id}/payments & /api/payments)
# ===========================================================================
@invoices_router.post(
    "/{invoice_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a payment against an invoice",
)
def register_payment(
    invoice_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
):
    """Register a full or partial payment against an invoice. Recomputes paid_amount and status automatically."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )

    pay_date = payload.payment_date or date.today()
    payment = Payment(
        invoice_id=invoice_id,
        amount=payload.amount,
        payment_date=pay_date,
        payment_method=payload.payment_method or "cash",
        notes=payload.notes,
    )
    db.add(payment)
    db.flush()

    # Recompute invoice paid_amount and status
    _recalculate_invoice_status(invoice, db)

    db.commit()
    db.refresh(payment)
    return payment


@invoices_router.get(
    "/{invoice_id}/payments",
    response_model=List[PaymentResponse],
    summary="List all payments registered for an invoice",
)
def list_invoice_payments(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieve all payment records for an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )

    return db.query(Payment).filter(Payment.invoice_id == invoice_id).order_by(Payment.payment_date.desc(), Payment.id.desc()).all()


@payments_router.delete(
    "/{payment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a payment and recompute invoice status",
)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    """Delete a payment and automatically recompute the parent invoice's paid_amount and status."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found",
        )

    invoice_id = payment.invoice_id
    db.delete(payment)
    db.flush()

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice:
        _recalculate_invoice_status(invoice, db)

    db.commit()
    return {"message": f"Payment #{payment_id} deleted successfully", "id": payment_id}
