"""
Official payment receipt (PDF) generation for the Smart Parking System.

Builds a professional, branded PDF bill for a successful Payment using
ReportLab. The logo is drawn as vector shapes (no external image asset
needed) so it always renders crisply and needs no static file to ship.

Usage:
    from payments.receipts import generate_receipt_pdf
    pdf_bytes = generate_receipt_pdf(payment)
"""
import io
from datetime import datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------
# Brand palette (mirrors the site's "Asphalt & Sensor" design system)
# ---------------------------------------------------------------------
ASPHALT_950 = colors.HexColor("#0A121C")
ASPHALT_900 = colors.HexColor("#0E1826")
ASPHALT_700 = colors.HexColor("#1C3049")
TRAFFIC_BLUE = colors.HexColor("#2F80ED")
TRAFFIC_BLUE_DEEP = colors.HexColor("#1254A1")
SIGNAL_GREEN = colors.HexColor("#2FBE72")
INK_900 = colors.HexColor("#0F1720")
INK_600 = colors.HexColor("#55677A")
INK_400 = colors.HexColor("#8A97A6")
INK_200 = colors.HexColor("#D3D9DF")
CONCRETE_50 = colors.HexColor("#F4F6F8")
LANE_WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

METHOD_LABELS = {
    "esewa": "eSewa Digital Wallet",
    "khalti": "Khalti Digital Wallet",
    "cash": "Cash on Arrival",
}


def _draw_logo_mark(c, x, y, size=11 * mm):
    """Draw the 'P' brand mark — a rounded square with the letter P — the
    same mark used in the site navbar, rendered as vector shapes."""
    c.saveState()
    c.setFillColor(TRAFFIC_BLUE)
    c.roundRect(x, y, size, size, 2.6 * mm, stroke=0, fill=1)
    c.setFillColor(LANE_WHITE)
    c.setFont("Helvetica-Bold", size * 0.62)
    c.drawCentredString(x + size / 2, y + size * 0.28, "P")
    c.restoreState()


def _header(c, site):
    """Dark letterhead band with logo, site name, and 'authorized' seal."""
    band_h = 34 * mm
    c.setFillColor(ASPHALT_950)
    c.rect(0, PAGE_H - band_h, PAGE_W, band_h, stroke=0, fill=1)

    # Thin traffic-blue accent line under the header band.
    c.setFillColor(TRAFFIC_BLUE)
    c.rect(0, PAGE_H - band_h - 1.2 * mm, PAGE_W, 1.2 * mm, stroke=0, fill=1)

    logo_size = 13 * mm
    logo_x = MARGIN
    logo_y = PAGE_H - band_h / 2 - logo_size / 2
    _draw_logo_mark(c, logo_x, logo_y, logo_size)

    text_x = logo_x + logo_size + 6.5 * mm
    c.setFillColor(LANE_WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(text_x, PAGE_H - band_h / 2 + 2.5 * mm, site["SITE_NAME"])
    c.setFont("Helvetica", 8.5)
    c.setFillColor(INK_200)
    c.drawString(text_x, PAGE_H - band_h / 2 - 4.5 * mm, site["SITE_TAGLINE"].upper() + " \u2022 NEPAL")

    # Authorized-system seal, top-right.
    seal_w, seal_h = 46 * mm, 15 * mm
    seal_x = PAGE_W - MARGIN - seal_w
    seal_y = PAGE_H - band_h / 2 - seal_h / 2
    c.setStrokeColor(TRAFFIC_BLUE)
    c.setLineWidth(1)
    c.roundRect(seal_x, seal_y, seal_w, seal_h, 2 * mm, stroke=1, fill=0)
    c.setFillColor(LANE_WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(seal_x + seal_w / 2, seal_y + seal_h - 5.5 * mm, "AUTHORIZED SYSTEM")
    c.setFont("Helvetica", 7.6)
    c.setFillColor(INK_200)
    c.drawCentredString(seal_x + seal_w / 2, seal_y + 4.2 * mm, "Digitally generated \u2022 No signature required")

    return PAGE_H - band_h - 1.2 * mm


def _footer(c, site, page_num=1):
    foot_h = 22 * mm
    c.setFillColor(ASPHALT_950)
    c.rect(0, 0, PAGE_W, foot_h, stroke=0, fill=1)
    c.setFillColor(TRAFFIC_BLUE)
    c.rect(0, foot_h, PAGE_W, 1 * mm, stroke=0, fill=1)

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(LANE_WHITE)
    c.drawString(MARGIN, foot_h - 6.5 * mm, site["SITE_NAME"])
    c.setFont("Helvetica", 7.6)
    c.setFillColor(INK_200)
    contact_line = (
        f"{site['SUPPORT_ADDRESS']}  \u2022  {site['SUPPORT_PHONE']}  \u2022  {site['SUPPORT_EMAIL']}"
    )
    c.drawString(MARGIN, foot_h - 11.5 * mm, contact_line)
    c.setFont("Helvetica-Oblique", 7.2)
    c.drawString(
        MARGIN, foot_h - 16.5 * mm,
        "This is a computer-generated receipt issued by the ParkSmart Nepal Smart Parking System and is valid without a physical signature.",
    )
    c.setFont("Helvetica", 7.6)
    c.drawRightString(PAGE_W - MARGIN, foot_h - 6.5 * mm, f"Page {page_num}")


def _section_title(c, x, y, text):
    c.setFillColor(TRAFFIC_BLUE_DEEP)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x, y, text.upper())
    c.setStrokeColor(INK_200)
    c.setLineWidth(0.6)
    c.line(x, y - 2.2 * mm, PAGE_W - MARGIN, y - 2.2 * mm)


def _kv_row(c, x, y, label, value, label_w=42 * mm, value_font="Helvetica-Bold"):
    c.setFont("Helvetica", 8.6)
    c.setFillColor(INK_600)
    c.drawString(x, y, label)
    c.setFont(value_font, 9.2)
    c.setFillColor(INK_900)
    c.drawString(x + label_w, y, str(value))


def generate_receipt_pdf(payment):
    """Build and return the receipt PDF as raw bytes for `payment`.

    `payment` must be a payments.models.Payment instance whose status is
    "success" — the caller is responsible for that check (the view
    enforces it before calling this).
    """
    site = settings.SPS_SETTINGS
    reservation = payment.reservation
    lot = reservation.lot
    user = reservation.user

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    content_top = _header(c, site) - 12 * mm
    y = content_top

    # ---- Title row -----------------------------------------------------
    c.setFillColor(INK_900)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(MARGIN, y, "Payment Receipt")
    c.setFont("Helvetica", 8.8)
    c.setFillColor(INK_600)
    generated_on = datetime.now().strftime("%d %b %Y, %I:%M %p")
    c.drawRightString(PAGE_W - MARGIN, y, f"Generated: {generated_on}")
    y -= 5.5 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(INK_600)
    c.drawString(MARGIN, y, "Official record of a completed parking payment transaction.")

    # ---- PAID stamp + receipt no / date box ----------------------------
    y -= 10 * mm
    box_h = 20 * mm
    box_w = (PAGE_W - 2 * MARGIN - 6 * mm) / 2

    # Left box: Receipt identifiers
    c.setFillColor(CONCRETE_50)
    c.roundRect(MARGIN, y - box_h, box_w, box_h, 2 * mm, stroke=0, fill=1)
    c.setFont("Helvetica", 7.8)
    c.setFillColor(INK_600)
    c.drawString(MARGIN + 5 * mm, y - 6 * mm, "RECEIPT NO.")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(INK_900)
    c.drawString(MARGIN + 5 * mm, y - 11.5 * mm, f"RCPT-{payment.transaction_uuid[:10].upper()}")
    c.setFont("Helvetica", 7.8)
    c.setFillColor(INK_600)
    c.drawString(MARGIN + 5 * mm, y - 17 * mm, f"Booking Reference: {reservation.reference}")

    # Right box: Paid status stamp
    right_x = MARGIN + box_w + 6 * mm
    c.setFillColor(colors.HexColor("#E4F8ED") if payment.status == "success" else colors.HexColor("#FDEAEA"))
    c.roundRect(right_x, y - box_h, box_w, box_h, 2 * mm, stroke=0, fill=1)
    stamp_color = SIGNAL_GREEN if payment.status == "success" else colors.HexColor("#EF5757")
    c.setFillColor(stamp_color)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(right_x + box_w / 2, y - box_h / 2 + 1.6 * mm, payment.get_status_display().upper())
    c.setFont("Helvetica", 7.4)
    c.setFillColor(INK_600)
    if payment.paid_at:
        c.drawCentredString(right_x + box_w / 2, y - box_h / 2 - 5.2 * mm, payment.paid_at.strftime("on %d %b %Y, %I:%M %p"))

    y -= box_h + 10 * mm

    # ---- Customer & vehicle details ------------------------------------
    _section_title(c, MARGIN, y, "Customer & Vehicle Details")
    y -= 7 * mm
    col2_x = MARGIN + (PAGE_W - 2 * MARGIN) / 2

    customer_name = user.get_full_name() or user.username
    _kv_row(c, MARGIN, y, "Customer name", customer_name)
    _kv_row(c, col2_x, y, "Username", user.username)
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "Email", user.email or "\u2014")
    phone = getattr(getattr(user, "profile", None), "phone_number", "") or "\u2014"
    _kv_row(c, col2_x, y, "Phone", phone)
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "Vehicle number", reservation.vehicle_number)
    _kv_row(c, col2_x, y, "Vehicle type", reservation.get_vehicle_type_display())

    y -= 11 * mm

    # ---- Booking details -------------------------------------------------
    _section_title(c, MARGIN, y, "Parking Booking Details")
    y -= 7 * mm
    _kv_row(c, MARGIN, y, "Parking lot", lot.name)
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "City", lot.get_city_display())
    _kv_row(c, col2_x, y, "Assigned slot", reservation.slot.slot_number if reservation.slot else "Not assigned")
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "Address", lot.address, value_font="Helvetica")
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "Start time", reservation.start_time.strftime("%d %b %Y, %I:%M %p"))
    _kv_row(c, col2_x, y, "Duration", f"{reservation.duration_hours} hr")
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "End time", reservation.end_time.strftime("%d %b %Y, %I:%M %p"))

    y -= 11 * mm

    # ---- Payment breakdown table ------------------------------------------
    _section_title(c, MARGIN, y, "Payment Breakdown")
    y -= 8 * mm

    table_x = MARGIN
    table_w = PAGE_W - 2 * MARGIN
    row_h = 8 * mm
    header_h = 8 * mm

    c.setFillColor(ASPHALT_900)
    c.rect(table_x, y - header_h, table_w, header_h, stroke=0, fill=1)
    c.setFillColor(LANE_WHITE)
    c.setFont("Helvetica-Bold", 8.4)
    c.drawString(table_x + 4 * mm, y - header_h + 2.6 * mm, "DESCRIPTION")
    c.drawRightString(table_x + table_w - 42 * mm, y - header_h + 2.6 * mm, "RATE")
    c.drawRightString(table_x + table_w - 4 * mm, y - header_h + 2.6 * mm, "AMOUNT (NPR)")
    y -= header_h

    currency = site["CURRENCY_SYMBOL"]
    rows = [
        (
            f"Parking charge \u2014 {lot.name} ({reservation.get_vehicle_type_display()})",
            f"{currency} {reservation.hourly_rate} / hr \u00d7 {reservation.duration_hours} hr",
            reservation.total_amount,
        ),
    ]
    c.setStrokeColor(INK_200)
    c.setLineWidth(0.5)
    for i, (desc, rate_text, amount) in enumerate(rows):
        bg = CONCRETE_50 if i % 2 == 0 else LANE_WHITE
        c.setFillColor(bg)
        c.rect(table_x, y - row_h, table_w, row_h, stroke=0, fill=1)
        c.setFillColor(INK_900)
        c.setFont("Helvetica", 8.6)
        c.drawString(table_x + 4 * mm, y - row_h + 2.6 * mm, desc)
        c.setFillColor(INK_600)
        c.drawRightString(table_x + table_w - 42 * mm, y - row_h + 2.6 * mm, rate_text)
        c.setFillColor(INK_900)
        c.setFont("Helvetica-Bold", 8.6)
        c.drawRightString(table_x + table_w - 4 * mm, y - row_h + 2.6 * mm, f"{amount:,}")
        c.line(table_x, y - row_h, table_x + table_w, y - row_h)
        y -= row_h

    # Total row
    total_h = 11 * mm
    c.setFillColor(ASPHALT_950)
    c.rect(table_x, y - total_h, table_w, total_h, stroke=0, fill=1)
    c.setFillColor(LANE_WHITE)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(table_x + 4 * mm, y - total_h + 3.6 * mm, "TOTAL PAID")
    c.setFillColor(colors.HexColor("#8FD4A8"))
    c.setFont("Helvetica-Bold", 12.5)
    c.drawRightString(table_x + table_w - 4 * mm, y - total_h + 3.4 * mm, f"{currency} {payment.amount:,}")
    y -= total_h + 10 * mm

    # ---- Transaction / payment method details -----------------------------
    _section_title(c, MARGIN, y, "Transaction Details")
    y -= 7 * mm
    method_label = METHOD_LABELS.get(payment.method, payment.get_method_display())
    _kv_row(c, MARGIN, y, "Payment method", method_label)
    _kv_row(c, col2_x, y, "Transaction UUID", payment.transaction_uuid[:24])
    y -= 6.2 * mm
    _kv_row(c, MARGIN, y, "Gateway reference", payment.gateway_reference or "\u2014")
    _kv_row(c, col2_x, y, "Payment status", payment.get_status_display())
    y -= 6.2 * mm
    paid_at_text = payment.paid_at.strftime("%d %b %Y, %I:%M %p") if payment.paid_at else "\u2014"
    _kv_row(c, MARGIN, y, "Paid at", paid_at_text)
    _kv_row(c, col2_x, y, "Booking status", reservation.get_status_display())

    _footer(c, site)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
