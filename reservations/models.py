import math
import uuid
from django.utils.timesince import timesince
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from parking.models import ParkingLot, ParkingSlot


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("pending_payment", "Pending Payment"),
        ("confirmed", "Confirmed"),
        ("overstay", "Overstay"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
        ("cancelled", "Cancelled"),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="reservations")
    slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True, related_name="reservations")
    vehicle_type = models.CharField(max_length=10, choices=ParkingSlot.VEHICLE_CHOICES)
    vehicle_number = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    hourly_rate = models.PositiveIntegerField()
    total_amount = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_payment")
    created_at = models.DateTimeField(auto_now_add=True)

    # ---- Entry / exit tracking -------------------------------------------
    actual_entry_time = models.DateTimeField(null=True, blank=True)
    actual_exit_time = models.DateTimeField(null=True, blank=True)

    # ---- Overstay + fine (ONE fine per reservation, updated in place) -----
    overstay_minutes = models.PositiveIntegerField(default=0)
    fine_amount = models.PositiveIntegerField(default=0)
    fine_paid = models.BooleanField(default=False)
    fine_paid_at = models.DateTimeField(null=True, blank=True)

    # ---- Flags so each alert is sent only once ------------------------------
    expiry_warning_sent = models.BooleanField(default=False)
    overstay_notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"SPS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.user.username}"

    def get_absolute_url(self):
        return reverse("reservations:detail", kwargs={"reference": self.reference})

    @property
    def duration_hours(self):
        seconds = (self.end_time - self.start_time).total_seconds()
        return max(1, round(seconds / 3600))

    # ---- State helpers -----------------------------------------------------
    @property
    def is_checked_in(self):
        return self.actual_entry_time is not None and self.actual_exit_time is None

    @property
    def is_in_use(self):
        """Vehicle is physically inside (normal stay or overstay)."""
        return self.status in ("confirmed", "overstay") and self.is_checked_in

    @property
    def can_check_in(self):
        if self.status != "confirmed" or self.actual_entry_time:
            return False
        early = timedelta(minutes=settings.SPS_SETTINGS["CHECKIN_EARLY_MINUTES"])
        now = timezone.now()
        return self.start_time - early <= now <= self.end_time

    @property
    def fine_due(self):
        return self.fine_amount > 0 and not self.fine_paid

    # ---- Fine calculation ----------------------------------------------------
    def calculate_overstay(self, now=None):
        """Return (overstay_minutes, fine_amount).

        Overstay is counted from end_time. Nothing is charged until the grace
        period is exceeded; after that the fine is Rs. X for every started block.
        The result is one number that is overwritten on each check, so running
        the checker every minute can never create duplicate fines.
        """
        cfg = settings.SPS_SETTINGS
        now = self.actual_exit_time or now or timezone.now()
        delta = max(now - self.end_time, timedelta(0))
        minutes = int(delta.total_seconds() // 60)
        if minutes <= cfg["OVERSTAY_GRACE_MINUTES"]:
            return 0, 0
        blocks = math.ceil(minutes / cfg["OVERSTAY_FINE_INTERVAL_MINUTES"])
        return minutes, blocks * cfg["OVERSTAY_FINE_AMOUNT"]


class Notification(models.Model):
    KIND_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("danger", "Danger"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.TextField()
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    @property
    def time_ago(self):
        text = timesince(self.created_at)
        return "just now" if text.split()[0] == "0" else f"{text} ago"