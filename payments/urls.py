from django.urls import path

from . import views


app_name = "payments"


urlpatterns = [
    # Payment selection
    path("<str:reference>/esewa/", views.pay_esewa, name="pay_esewa"),

    # eSewa callbacks. These must NOT take a reference, because gateways.py reverses them with no args.
    path("esewa/success/", views.esewa_success, name="esewa_success"),
    path("esewa/failure/", views.esewa_failure, name="esewa_failure"),
    path("<str:reference>/",views.choose_payment,name="choose"),

    # eSewa
    path(
        "<str:reference>/esewa/",
        views.pay_esewa,
        name="esewa_pay",
    ),

    path(
        "esewa/callback/",
        views.esewa_callback,
        name="esewa_callback",
    ),

    # Khalti
    path(
        "<str:reference>/khalti/",
        views.pay_khalti,
        name="khalti_pay",
    ),

    path(
        "<str:reference>/khalti/demo-confirm/",
        views.khalti_demo_confirm,
        name="khalti_demo_confirm",
    ),

    path(
        "khalti/callback/",
        views.khalti_callback,
        name="khalti_callback",
    ),

    # Cash
    path(
        "<str:reference>/cash/",
        views.pay_cash,
        name="cash_pay",
    ),

    # PDF receipt
    path(
        "<str:reference>/receipt/",
        views.receipt_pdf,
        name="receipt_pdf",
    ),

    # QR verification
    path(
        "verify/<str:transaction_uuid>/",
        views.verify_payment,
        name="verify_payment",
    ),
]