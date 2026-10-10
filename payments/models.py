import uuid

from django.db import models

from reservations.models import Reservation


def generate_transaction_uuid():
    """Named function (not a lambda) so Django can write it into migrations."""
    return f"PSN-{uuid.uuid4().hex[:20]}"


class Payment(models.Model):

    METHOD_CHOICES = [
        ("esewa", "eSewa"),
        ("khalti", "Khalti"),
        ("cash", "Cash"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    transaction_uuid = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        default=generate_transaction_uuid,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    gateway_reference = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.reservation.reference} - "
            f"{self.method} - {self.status}"
        )