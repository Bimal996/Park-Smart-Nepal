"""
Payment gateway helpers for eSewa (ePay v2) and Khalti (KPG-2).

eSewa flow (v2):
  1. We POST a signed form to eSewa.
  2. eSewa redirects the browser to our success_url with  ?data=<base64 JSON>.
  3. We decode `data`, verify its HMAC signature, (optionally) ask eSewa's
     status API, and only then mark the reservation as paid.
"""
import base64
import hashlib
import hmac
import json
from decimal import Decimal

import requests
from django.conf import settings
from django.urls import reverse

ESEWA_FORM_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"            # UAT/test endpoint
ESEWA_STATUS_URL = "https://rc.esewa.com.np/api/epay/transaction/status/"        # UAT/test status check
KHALTI_INITIATE_URL = "https://a.khalti.com/api/v2/epayment/initiate/"
KHALTI_LOOKUP_URL = "https://a.khalti.com/api/v2/epayment/lookup/"

ESEWA_TEST_SECRET = "8gBm/:&EnhH.1/q"  # eSewa's public sandbox key for merchant code EPAYTEST


def esewa_product_code():
    cfg = settings.SPS_SETTINGS
    return cfg.get("ESEWA_PRODUCT_CODE") or cfg.get("ESEWA_MERCHANT_CODE") or "EPAYTEST"


def esewa_secret_key():
    if esewa_product_code() == "EPAYTEST":
        return ESEWA_TEST_SECRET
    return settings.SPS_SETTINGS.get("ESEWA_SECRET_KEY", "")


def _sign(message):
    digest = hmac.new(esewa_secret_key().encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def esewa_signature(total_amount, transaction_uuid, product_code):
    """Signature for the request form (fields in eSewa's fixed order)."""
    return _sign(
        f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    )


def esewa_amount(value):
    """Amount as eSewa expects it: '90' for whole rupees, '90.50' otherwise.

    The SAME string must be used in the form, the signature and the status check.
    """
    value = Decimal(str(value))
    return str(int(value)) if value == value.to_integral_value() else f"{value:.2f}"


def build_esewa_payload(request, payment):
    """Form fields for eSewa's ePay v2 endpoint.

    IMPORTANT: success_url / failure_url must NOT contain a query string.
    eSewa appends '?data=...' itself, so '?status=success' made the URL
    '...?status=success?data=...' and the payment was never recognised.
    """
    product_code = esewa_product_code()
    amount = esewa_amount(payment.amount)
    return {
        "amount": amount,
        "tax_amount": 0,
        "total_amount": amount,
        "transaction_uuid": payment.transaction_uuid,
        "product_code": product_code,
        "product_service_charge": 0,
        "product_delivery_charge": 0,
        "success_url": request.build_absolute_uri(reverse("payments:esewa_success")),
        "failure_url": request.build_absolute_uri(reverse("payments:esewa_failure")),
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": esewa_signature(amount, payment.transaction_uuid, product_code),
    }


def decode_esewa_response(encoded):
    """Decode eSewa's base64 `data` and verify its signature.

    Returns the decoded dict if the signature is valid, otherwise None.
    """
    if not encoded:
        return None
    try:
        encoded = encoded.strip().replace(" ", "+")      # '+' turns into ' ' in query strings
        encoded += "=" * (-len(encoded) % 4)              # restore base64 padding
        data = json.loads(base64.b64decode(encoded).decode("utf-8"))
        names = [n for n in str(data.get("signed_field_names", "")).split(",") if n]
        message = ",".join(f"{n}={data.get(n, '')}" for n in names)
        expected = _sign(message)
        if hmac.compare_digest(expected, str(data.get("signature", ""))):
            return data
    except Exception:
        return None
    return None


def esewa_status_check(product_code, total_amount, transaction_uuid):
    """Ask eSewa for the transaction status ('COMPLETE', 'PENDING', ...).

    Returns None when eSewa can't be reached, so a local/offline demo still works
    (the signed response has already been verified before this is called).
    """
    try:
        resp = requests.get(
            ESEWA_STATUS_URL,
            params={
                "product_code": product_code,
                "total_amount": total_amount,
                "transaction_uuid": transaction_uuid,
            },
            timeout=8,
        )
        if resp.status_code == 200:
            return resp.json().get("status")
    except (requests.RequestException, ValueError):
        pass
    return None