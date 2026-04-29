import io
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# Brand colours
GOLD = colors.HexColor('#B8962E')
BLACK = colors.HexColor('#0A0A0A')
DARK = colors.HexColor('#2D2D2D')
LIGHT_GREY = colors.HexColor('#F5F5F5')
MID_GREY = colors.HexColor('#888888')


def generate_invoice(registration):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=28,
        textColor=BLACK,
        fontName='Helvetica-Bold',
        spaceAfter=4,
    )
    gold_style = ParagraphStyle(
        'Gold',
        parent=styles['Normal'],
        fontSize=11,
        textColor=GOLD,
        fontName='Helvetica',
        spaceAfter=2,
    )
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=MID_GREY,
        fontName='Helvetica',
    )
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=11,
        textColor=DARK,
        fontName='Helvetica',
    )
    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        fontSize=10,
        textColor=MID_GREY,
        alignment=TA_CENTER,
    )

    # Generate invoice number
    invoice_number = f"INV-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"

    story = []

    # Header
    story.append(Paragraph("HouseParty", title_style))
    story.append(Paragraph("PRIVATE EVENT INVOICE", gold_style))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=12))

    # Invoice meta
    meta_data = [
        ['Invoice Number', invoice_number],
        ['Date', registration.registered_at.strftime('%d %B %Y, %I:%M %p') if registration.registered_at else 'N/A'],
        ['Payment Reference', registration.payment_reference or 'N/A'],
    ]

    meta_table = Table(meta_data, colWidths=[60*mm, 110*mm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), MID_GREY),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD'), spaceAfter=12))

    # Registrant details
    story.append(Paragraph("REGISTRANT DETAILS", gold_style))
    story.append(Spacer(1, 6))

    reg_data = [
        ['Full Name', registration.full_name],
        ['Email', registration.email],
        ['Phone', registration.phone],
    ]
    reg_table = Table(reg_data, colWidths=[60*mm, 110*mm])
    reg_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), MID_GREY),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(reg_table)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD'), spaceAfter=12))

    # Event details
    story.append(Paragraph("EVENT DETAILS", gold_style))
    story.append(Spacer(1, 6))

    event_data = [
        ['Event', registration.event.name],
        ['Date', registration.event.date.strftime('%A, %d %B %Y')],
        ['Time', registration.event.start_time.strftime('%I:%M %p')],
        ['Zone', registration.event.zone],
        ['Ticket Tier', registration.tier.name],
        ['Inclusions', registration.tier.inclusions],
    ]
    event_table = Table(event_data, colWidths=[60*mm, 110*mm])
    event_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), MID_GREY),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(event_table)
    story.append(Spacer(1, 16))

    # Amount box
    amount_data = [
        ['AMOUNT PAID', f"₦{registration.amount_paid:,.2f}"]
    ]
    amount_table = Table(amount_data, colWidths=[130*mm, 40*mm])
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (0, 0), MID_GREY),
        ('TEXTCOLOR', (1, 0), (1, 0), GOLD),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(amount_table)
    story.append(Spacer(1, 24))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD'), spaceAfter=8))
    story.append(Paragraph(
        "Your full event address will be sent 24 hours before the event. "
        "Please keep this invoice as proof of registration. "
        "All sales are final.",
        center_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Private · Exclusive · Adult Only", center_style))

    doc.build(story)
    buffer.seek(0)
    return buffer