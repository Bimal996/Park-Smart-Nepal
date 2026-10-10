import base64
import hashlib
import hmac
import json
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from reservations.models import Reservation

from .gateways import (
    ESEWA_FORM_URL,
    KHALTI_INITIATE_URL,
    KHALTI_LOOKUP_URL,
    build_esewa_payload,
)
from .models import Payment
from .receipts import generate_receipt_pdf


# ---------------------------------------------------------------------
# PAYMENT HELPERS
# ---------------------------------------------------------------------

def _get_or_create_payment(reservation, method):
    payment, _ = Payment.objects.get_or_create(
        reservation=reservation,
        defaults={
            "method": method,
            "amount": reservation.total_amount,
        },
    )

    payment.method = method
    payment.amount = reservation.total_amount
    payment.save(
        update_fields=["method", "amount"]
    )

    return payment


def _confirm_reservation(payment, gateway_reference=""):
    payment.status = "success"
    payment.paid_at = timezone.now()
    payment.gateway_reference = gateway_reference
    payment.save(
        update_fields=[
            "status",
            "paid_at",
            "gateway_reference",
        ]
    )

    reservation = payment.reservation

    reservation.status = "confirmed"
    reservation.save(update_fields=["status"])

    if reservation.slot:
        reservation.slot.status = "occupied"
        reservation.slot.save(update_fields=["status"])


# ---------------------------------------------------------------------
# PAYMENT SELECTION
# ---------------------------------------------------------------------

@login_required
def choose_payment(request, reference):
    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    if reservation.status != "pending_payment":
        return redirect(
            "reservations:detail",
            reference=reference,
        )

    return render(
        request,
        "payments/choose.html",
        {
            "reservation": reservation,
        },
    )


# ---------------------------------------------------------------------
# ESEWA
# ---------------------------------------------------------------------

@login_required
def pay_esewa(request, reference):
    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    payment = _get_or_create_payment(
        reservation,
        "esewa",
    )

    payload = build_esewa_payload(
        request,
        payment,
    )

    return render(
        request,
        "payments/esewa_redirect.html",
        {
            "esewa_url": ESEWA_FORM_URL,
            "payload": payload,
            "reservation": reservation,
        },
    )


def esewa_callback(request):
    """
    eSewa redirects the browser here after payment.

    The current implementation supports the sandbox/demo flow.
    """

    status = request.GET.get("status")

    txn_uuid = (
        request.GET.get("transaction_uuid")
        or request.session.get("last_txn_uuid")
    )

    payment = (
        Payment.objects.filter(
            transaction_uuid=txn_uuid
        ).first()
        if txn_uuid
        else None
    )

    if not payment:
        messages.error(
            request,
            "We couldn't locate that transaction.",
        )
        return redirect("pages:home")

    if status == "success":
        _confirm_reservation(
            payment,
            gateway_reference=(
                f"ESW-{payment.transaction_uuid[:8]}"
            ),
        )

        messages.success(
            request,
            (
                f"Payment successful! "
                f"Reservation {payment.reservation.reference} "
                f"is confirmed."
            ),
        )

    else:
        payment.status = "failed"
        payment.save(update_fields=["status"])

        messages.error(
            request,
            (
                "eSewa payment was not completed. "
                "You can try again."
            ),
        )

    return redirect(
        "reservations:detail",
        reference=payment.reservation.reference,
    )


# ---------------------------------------------------------------------
# KHALTI
# ---------------------------------------------------------------------

@login_required
def pay_khalti(request, reference):
    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    payment = _get_or_create_payment(
        reservation,
        "khalti",
    )

    secret_key = settings.SPS_SETTINGS.get(
        "KHALTI_SECRET_KEY"
    )

    if secret_key:
        try:
            response = requests.post(
                KHALTI_INITIATE_URL,
                headers={
                    "Authorization": f"key {secret_key}"
                },
                json={
                    "return_url": request.build_absolute_uri(
                        reverse(
                            "payments:khalti_callback"
                        )
                    ),
                    "website_url": request.build_absolute_uri(
                        "/"
                    ),
                    "amount": int(payment.amount * 100),
                    "purchase_order_id": (
                        payment.transaction_uuid
                    ),
                    "purchase_order_name": (
                        f"SPS Reservation "
                        f"{reservation.reference}"
                    ),
                },
                timeout=8,
            )

            data = response.json()

            if (
                response.status_code == 200
                and data.get("payment_url")
            ):
                return redirect(
                    data["payment_url"]
                )

        except requests.RequestException:
            pass

        except ValueError:
            pass

    # Demo mode
    return render(
        request,
        "payments/khalti_demo.html",
        {
            "reservation": reservation,
            "payment": payment,
        },
    )


@login_required
def khalti_demo_confirm(request, reference):
    """
    Simulated Khalti confirmation when no live
    Khalti secret key is configured.
    """

    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    payment = get_object_or_404(
        Payment,
        reservation=reservation,
    )

    if request.method == "POST":
        _confirm_reservation(
            payment,
            gateway_reference=(
                f"KHL-DEMO-{payment.transaction_uuid[:8]}"
            ),
        )

        messages.success(
            request,
            (
                f"Payment successful! "
                f"Reservation {reservation.reference} "
                f"is confirmed."
            ),
        )

        return redirect(
            "reservations:detail",
            reference=reservation.reference,
        )

    return redirect(
        "payments:khalti_pay",
        reference=reference,
    )


def khalti_callback(request):
    pidx = request.GET.get("pidx")

    txn_uuid = request.GET.get(
        "purchase_order_id"
    )

    payment = (
        Payment.objects.filter(
            transaction_uuid=txn_uuid
        ).first()
    )

    if not payment:
        messages.error(
            request,
            "We couldn't locate that transaction.",
        )
        return redirect("pages:home")

    secret_key = settings.SPS_SETTINGS.get(
        "KHALTI_SECRET_KEY"
    )

    verified = False

    if secret_key and pidx:
        try:
            response = requests.post(
                KHALTI_LOOKUP_URL,
                headers={
                    "Authorization": f"key {secret_key}"
                },
                json={
                    "pidx": pidx
                },
                timeout=8,
            )

            data = response.json()

            verified = (
                response.status_code == 200
                and data.get("status") == "Completed"
            )

        except (
            requests.RequestException,
            ValueError,
        ):
            verified = False

    if verified:
        _confirm_reservation(
            payment,
            gateway_reference=pidx,
        )

        messages.success(
            request,
            (
                f"Payment successful! "
                f"Reservation "
                f"{payment.reservation.reference} "
                f"is confirmed."
            ),
        )

    else:
        payment.status = "failed"
        payment.save(update_fields=["status"])

        messages.error(
            request,
            (
                "Khalti payment could not be "
                "verified. Please try again."
            ),
        )

    return redirect(
        "reservations:detail",
        reference=payment.reservation.reference,
    )


# ---------------------------------------------------------------------
# CASH PAYMENT
# ---------------------------------------------------------------------

@login_required
def pay_cash(request, reference):
    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    if request.method == "POST":
        payment = _get_or_create_payment(
            reservation,
            "cash",
        )

        payment.status = "success"
        payment.paid_at = timezone.now()
        payment.gateway_reference = "PAY-AT-GATE"

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "gateway_reference",
            ]
        )

        reservation.status = "confirmed"
        reservation.save(update_fields=["status"])

        if reservation.slot:
            reservation.slot.status = "occupied"
            reservation.slot.save(
                update_fields=["status"]
            )

        messages.success(
            request,
            (
                f"Reservation {reservation.reference} "
                f"confirmed. Please pay Rs. "
                f"{reservation.total_amount} in cash "
                f"at the gate."
            ),
        )

        return redirect(
            "reservations:detail",
            reference=reservation.reference,
        )

    return render(
        request,
        "payments/cash_confirm.html",
        {
            "reservation": reservation
        },
    )


# ---------------------------------------------------------------------
# PDF RECEIPT
# ---------------------------------------------------------------------

@login_required
def receipt_pdf(request, reference):
    """
    Download the official PDF receipt for a successful payment.
    """

    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    payment = get_object_or_404(
        Payment,
        reservation=reservation,
        status="success",
    )

    pdf_bytes = generate_receipt_pdf(
        payment
    )

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; '
        f'filename="ParkSmart-Receipt-'
        f'{reservation.reference}.pdf"'
    )

    return response


# ---------------------------------------------------------------------
# QR PAYMENT VERIFICATION
# ---------------------------------------------------------------------

def verify_payment(request, transaction_uuid):
    """
    Public verification endpoint used by the QR code
    printed on the PDF receipt.
    """

    payment = get_object_or_404(
        Payment,
        transaction_uuid=transaction_uuid,
        status="success",
    )

    reservation = payment.reservation
    lot = reservation.lot

    paid_at = (
        payment.paid_at.strftime(
            "%d %b %Y, %I:%M %p"
        )
        if payment.paid_at
        else "—"
    )

    try:
        method_label = payment.get_method_display()
    except AttributeError:
        method_label = payment.method

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width,
            initial-scale=1.0"
        >

        <title>
            Payment Verification —
            ParkSmart Nepal
        </title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                padding: 30px 15px;
                font-family:
                    Arial, Helvetica, sans-serif;
                background: #f4f6f8;
                color: #0f1720;
            }}

            .container {{
                width: 100%;
                max-width: 680px;
                margin: 0 auto;
            }}

            .card {{
                background: #ffffff;
                border-radius: 18px;
                padding: 30px;
                box-shadow:
                    0 10px 35px
                    rgba(0, 0, 0, 0.08);
            }}

            .brand {{
                font-size: 27px;
                font-weight: 800;
                color: #2f80ed;
            }}

            .tagline {{
                margin-top: 4px;
                color: #667085;
                font-size: 14px;
            }}

            .verified {{
                display: inline-block;
                margin: 22px 0;
                padding: 10px 17px;
                background: #e4f8ed;
                color: #218653;
                border-radius: 999px;
                font-size: 14px;
                font-weight: 700;
            }}

            .row {{
                display: flex;
                justify-content: space-between;
                gap: 25px;
                padding: 14px 0;
                border-bottom:
                    1px solid #e5e7eb;
            }}

            .label {{
                color: #667085;
                font-size: 14px;
            }}

            .value {{
                max-width: 60%;
                text-align: right;
                font-weight: 700;
                overflow-wrap: anywhere;
            }}

            .amount {{
                margin-top: 24px;
                padding: 18px 20px;
                border-radius: 13px;
                background: #0a121c;
                color: #ffffff;
                display: flex;
                align-items: center;
                justify-content:
                    space-between;
                gap: 20px;
                font-size: 18px;
                font-weight: 800;
            }}

            .footer {{
                margin-top: 24px;
                padding-top: 18px;
                border-top:
                    1px solid #e5e7eb;
                text-align: center;
                color: #667085;
                font-size: 12px;
                line-height: 1.6;
            }}

            @media (max-width: 600px) {{
                body {{
                    padding: 15px 10px;
                }}

                .card {{
                    padding: 20px;
                    border-radius: 14px;
                }}

                .brand {{
                    font-size: 23px;
                }}

                .row {{
                    display: block;
                }}

                .value {{
                    max-width: 100%;
                    margin-top: 5px;
                    text-align: left;
                }}

                .amount {{
                    font-size: 16px;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="container">
            <div class="card">

                <div class="brand">
                    ParkSmart Nepal
                </div>

                <div class="tagline">
                    Smart Parking System
                </div>

                <div class="verified">
                    ✓ PAYMENT VERIFIED
                </div>

                <div class="row">
                    <div class="label">
                        Booking Reference
                    </div>
                    <div class="value">
                        {reservation.reference}
                    </div>
                </div>

                <div class="row">
                    <div class="label">
                        Transaction UUID
                    </div>
                    <div class="value">
                        {payment.transaction_uuid}
                    </div>
                </div>

                <div class="row">
                    <div class="label">
                        Parking Lot
                    </div>
                    <div class="value">
                        {lot.name}
                    </div>
                </div>

                <div class="row">
                    <div class="label">
                        Payment Method
                    </div>
                    <div class="value">
                        {method_label}
                    </div>
                </div>

                <div class="row">
                    <div class="label">
                        Paid At
                    </div>
                    <div class="value">
                        {paid_at}
                    </div>
                </div>

                <div class="amount">
                    <span>
                        Amount Paid
                    </span>

                    <span>
                        Rs. {payment.amount}
                    </span>
                </div>

                <div class="footer">
                    This payment has been successfully
                    verified by ParkSmart Nepal.
                    <br>
                    Smart Parking System • Nepal
                </div>

            </div>
        </div>
    </body>
    </html>
    """

    return HttpResponse(html)

def _verify_esewa_signature(data: dict) -> bool:
    secret = settings.SPS_SETTINGS["ESEWA_SECRET_KEY"]
    signed_fields = data.get("signed_field_names", "").split(",")
    message = ",".join(f"{f}={data.get(f, '')}" for f in signed_fields)
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, data.get("signature", ""))


@login_required
def esewa_success(request):
    encoded = request.GET.get("data")
    if not encoded:
        messages.error(request, "Invalid eSewa response.")
        return redirect("pages:dashboard")

    try:
        data = json.loads(base64.b64decode(encoded).decode())
    except (ValueError, json.JSONDecodeError):
        messages.error(request, "Could not read eSewa response.")
        return redirect("pages:dashboard")

    if not _verify_esewa_signature(data) or data.get("status") != "COMPLETE":
        messages.error(request, "Payment verification failed.")
        return redirect("pages:dashboard")

    # transaction_uuid is what you sent in build_esewa_payload.
    txn_uuid = data["transaction_uuid"]

    # --- ADAPT TO YOUR MODELS: find the payment and mark it paid ---
    # payment = Payment.objects.get(transaction_uuid=txn_uuid)
    # payment.status = "paid"
    # payment.save()
    # generate_receipt(payment)   # your ReportLab receipt function
    # return redirect("payments:detail", reference=payment.reservation.reference)

    messages.success(request, "Payment successful via eSewa.")
    return redirect("pages:dashboard")


@login_required
def esewa_failure(request):
    messages.error(request, "eSewa payment was cancelled or failed.")
    return redirect("pages:dashboard")