import io
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from backend.models import Invoice, ClinicSettings


def format_dzd(amount: Optional[Decimal | float | int]) -> str:
    """Formats an amount into French DZD currency format (e.g. 12 500,00 DZD)."""
    if amount is None:
        val = 0.0
    else:
        val = float(amount)
    # Format with 2 decimal places and space as thousand separator
    formatted = f"{val:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} DZD"


def format_date_fr(d: Optional[date | datetime | str]) -> str:
    """Formats a date object or ISO string to DD/MM/YYYY."""
    if not d:
        return ""
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    try:
        parsed = date.fromisoformat(str(d).split("T")[0])
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return str(d)


def get_payment_method_fr(method: Optional[str]) -> str:
    """Translates payment method code to French label."""
    mapping = {
        "cash": "Espèces",
        "card": "Carte bancaire",
        "transfer": "Virement bancaire",
        "other": "Autre",
    }
    return mapping.get((method or "").lower(), method or "Espèces")


def generate_invoice_pdf(invoice: Invoice, settings: Optional[ClinicSettings] = None) -> bytes:
    """
    Generates a professional A4 PDF invoice in memory using ReportLab.
    Returns the PDF as raw bytes.
    """
    buffer = io.BytesIO()

    # Document geometry: A4 (595.27 x 841.89 pt), 36pt (0.5 inch) margins -> Printable width = 523.27 pt
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    printable_width = doc.width  # ~523.27 pt

    # Palette
    c_primary = colors.HexColor("#1E3A8A")     # Deep Navy Blue
    c_secondary = colors.HexColor("#2563EB")   # Medical Blue
    c_dark = colors.HexColor("#0F172A")        # Dark slate
    c_muted = colors.HexColor("#64748B")       # Muted gray
    c_border = colors.HexColor("#E2E8F0")      # Light gray border
    c_bg_light = colors.HexColor("#F8FAFC")    # Background light
    c_bg_alt = colors.HexColor("#F1F5F9")      # Alternating row

    # Typography & Styles
    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_primary,
        alignment=TA_RIGHT,
    )

    clinic_name_style = ParagraphStyle(
        "ClinicName",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=c_primary,
    )

    doctor_style = ParagraphStyle(
        "DoctorName",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=c_secondary,
    )

    clinic_details_style = ParagraphStyle(
        "ClinicDetails",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_muted,
    )

    invoice_meta_style = ParagraphStyle(
        "InvoiceMeta",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_dark,
        alignment=TA_RIGHT,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=c_primary,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=c_dark,
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    body_right = ParagraphStyle(
        "BodyRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )

    table_header_right = ParagraphStyle(
        "TableHeaderRight",
        parent=table_header_style,
        alignment=TA_RIGHT,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=c_muted,
        alignment=TA_CENTER,
    )

    story = []

    # -----------------------------------------------------------------------
    # 1. Header Section: Clinic Info (Left) & Invoice Meta (Right)
    # -----------------------------------------------------------------------
    clinic_name = (settings.clinic_name if settings and settings.clinic_name else "Cabinet Dentaire")
    doctor_name = (settings.doctor_name if settings and settings.doctor_name else "Chirurgien-Dentiste")
    clinic_phone = (settings.phone if settings and settings.phone else "")
    clinic_address = (settings.address if settings and settings.address else "")

    clinic_text = f"<b>{clinic_name}</b>"
    if doctor_name:
        clinic_text += f"<br/><font color='#2563EB'><b>{doctor_name}</b></font>"
    if clinic_address:
        clinic_text += f"<br/>{clinic_address}"
    if clinic_phone:
        clinic_text += f"<br/>Tél : {clinic_phone}"

    invoice_number = invoice.invoice_number or f"FAC-{invoice.id:04d}"
    invoice_date_str = format_date_fr(invoice.invoice_date)

    meta_text = (
        f"<font color='#1E3A8A'><b>FACTURE</b></font><br/>"
        f"<b>N° Facture :</b> {invoice_number}<br/>"
        f"<b>Date d'émission :</b> {invoice_date_str}"
    )

    header_table_data = [
        [
            Paragraph(clinic_text, body_style),
            Paragraph(meta_text, invoice_meta_style),
        ]
    ]

    header_table = Table(
        header_table_data,
        colWidths=[printable_width * 0.55, printable_width * 0.45],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceBefore=0, spaceAfter=14))

    # -----------------------------------------------------------------------
    # 2. Patient Information Card & Payment Status Badge
    # -----------------------------------------------------------------------
    patient = invoice.patient
    patient_name = patient.full_name if patient else "Patient Divers"
    patient_phone = patient.phone if patient and patient.phone else "Non renseigné"
    patient_address = patient.address if patient and patient.address else "Non renseignée"

    patient_card_html = (
        f"<b>PATIENT(E) :</b><br/>"
        f"<font size='10.5' color='#0F172A'><b>{patient_name}</b></font><br/>"
        f"<font color='#64748B'>Téléphone :</font> {patient_phone}<br/>"
        f"<font color='#64748B'>Adresse :</font> {patient_address}"
    )

    # Status Badge Configuration
    status_code = (invoice.status or "unpaid").lower()
    if status_code == "paid":
        status_label = "FACTURE ACQUITTÉE / PAYÉE"
        status_bg = colors.HexColor("#DCFCE7")  # Light green
        status_fg = "#16A34A"                   # Green text
    elif status_code == "partially_paid":
        status_label = "PARTIELLEMENT PAYÉE"
        status_bg = colors.HexColor("#FEF3C7")  # Light amber
        status_fg = "#D97706"                   # Amber text
    else:
        status_label = "EN ATTENTE DE PAIEMENT"
        status_bg = colors.HexColor("#FEE2E2")  # Light red
        status_fg = "#DC2626"                   # Red text

    status_badge_html = (
        f"<div align='center'>"
        f"<font color='{status_fg}'><b>● STATUT DU RÈGLEMENT</b></font><br/>"
        f"<font size='10' color='{status_fg}'><b>{status_label}</b></font>"
        f"</div>"
    )

    info_card_data = [
        [
            Paragraph(patient_card_html, body_style),
            Paragraph(status_badge_html, body_style),
        ]
    ]

    info_card_table = Table(
        info_card_data,
        colWidths=[printable_width * 0.60, printable_width * 0.40],
    )
    info_card_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), c_bg_light),
        ("BACKGROUND", (1, 0), (1, 0), status_bg),
        ("BOX", (0, 0), (0, 0), 0.75, c_border),
        ("BOX", (1, 0), (1, 0), 0.75, colors.HexColor(status_fg)),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(info_card_table)

    story.append(Spacer(1, 16))

    # -----------------------------------------------------------------------
    # 3. Prestations / Line Items Table
    # -----------------------------------------------------------------------
    story.append(Paragraph("DÉTAIL DES ACTES & PRESTATIONS", section_header_style))
    story.append(Spacer(1, 6))

    table_data = [
        [
            Paragraph("N°", table_header_style),
            Paragraph("Désignation de l'acte / Prestation", table_header_style),
            Paragraph("Montant", table_header_right),
        ]
    ]

    items = invoice.items or []
    if items:
        for idx, item in enumerate(items, start=1):
            table_data.append([
                Paragraph(str(idx), body_style),
                Paragraph(item.description or "Soin dentaire", body_style),
                Paragraph(format_dzd(item.amount), body_right),
            ])
    else:
        table_data.append([
            Paragraph("1", body_style),
            Paragraph("Consultation & Soins dentaires", body_style),
            Paragraph(format_dzd(invoice.total_amount), body_right),
        ])

    items_table = Table(
        table_data,
        colWidths=[35, printable_width - 155, 120],
    )
    
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), c_primary),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
    ]

    # Alternating row colors
    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(("BACKGROUND", (0, r), (-1, r), c_bg_alt))

    items_table.setStyle(TableStyle(t_style))
    story.append(items_table)

    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # 4. Financial Summary (Total, Paid, Balance Remaining)
    # -----------------------------------------------------------------------
    total_amount = Decimal(str(invoice.total_amount or 0.0))
    paid_amount = Decimal(str(invoice.paid_amount or 0.0))
    balance_due = total_amount - paid_amount
    if balance_due < Decimal("0.00"):
        balance_due = Decimal("0.00")

    summary_data = [
        [
            Paragraph("<b>Total Facturé :</b>", body_style),
            Paragraph(f"<b>{format_dzd(total_amount)}</b>", body_right),
        ],
        [
            Paragraph("<b>Montant Réglé :</b>", body_style),
            Paragraph(f"<font color='#16A34A'><b>{format_dzd(paid_amount)}</b></font>", body_right),
        ],
        [
            Paragraph("<b>Reste à Payer :</b>", ParagraphStyle("RedLabel", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#DC2626"))),
            Paragraph(f"<font color='#DC2626'><b>{format_dzd(balance_due)}</b></font>", ParagraphStyle("RedVal", parent=body_right, fontName="Helvetica-Bold")),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[120, 130],
    )
    summary_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#DC2626")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FEF2F2")),
    ]))

    # Wrap summary in a right-aligned container
    summary_container = Table(
        [[Paragraph("", body_style), summary_table]],
        colWidths=[printable_width - 250, 250],
    )
    summary_container.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(summary_container)

    story.append(Spacer(1, 16))

    # -----------------------------------------------------------------------
    # 5. Payments History Section (Historique des Règlements)
    # -----------------------------------------------------------------------
    payments = invoice.payments or []
    story.append(Paragraph("HISTORIQUE DES RÈGLEMENTS", section_header_style))
    story.append(Spacer(1, 6))

    if payments:
        pay_table_data = [
            [
                Paragraph("Date", table_header_style),
                Paragraph("Mode de règlement", table_header_style),
                Paragraph("Montant réglé", table_header_right),
                Paragraph("Observations / Réf", table_header_style),
            ]
        ]
        for p in payments:
            pay_date_str = format_date_fr(p.payment_date)
            method_str = get_payment_method_fr(p.payment_method)
            p_notes = p.notes or "-"
            pay_table_data.append([
                Paragraph(pay_date_str, body_style),
                Paragraph(method_str, body_style),
                Paragraph(f"<b>{format_dzd(p.amount)}</b>", body_right),
                Paragraph(p_notes, body_style),
            ])

        pay_table = Table(
            pay_table_data,
            colWidths=[80, 130, 110, printable_width - 320],
        )
        p_style = [
            ("BACKGROUND", (0, 0), (-1, 0), c_secondary),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ]
        for r in range(1, len(pay_table_data)):
            if r % 2 == 0:
                p_style.append(("BACKGROUND", (0, r), (-1, r), c_bg_alt))
        pay_table.setStyle(TableStyle(p_style))
        story.append(pay_table)
    else:
        no_pay_box = Table(
            [[Paragraph("<font color='#64748B'><i>Aucun règlement enregistré sur cette facture à ce jour.</i></font>", body_style)]],
            colWidths=[printable_width],
        )
        no_pay_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_bg_light),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(no_pay_box)

    story.append(Spacer(1, 24))

    # -----------------------------------------------------------------------
    # 6. Footer (Mention & Certification)
    # -----------------------------------------------------------------------
    generation_date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    footer_text = (
        f"Document émis par <b>{clinic_name}</b> le {generation_date_str}<br/>"
        f"Pour toute question concernant cette facture, veuillez contacter le cabinet."
    )
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_border, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph(footer_text, footer_style))

    # Build PDF
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()
