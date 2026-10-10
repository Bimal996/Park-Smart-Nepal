"""Slot lifecycle automation: expiry warnings, overstay detection, fines, no-shows.

Called by:
  * `python manage.py check_overstays`   (scheduled / looped)
  * the notification bell (context processor + live feed) and My Bookings
Every step is idempotent: running it 100 times gives the same result as once.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Notification, Reservation


def notify(user, title, message, kind="info", reservation=None):
    """Create one in-app notification (shown in the navbar bell)."""
    return Notification.objects.create(
        user=user, reservation=reservation, title=title, message=message, kind=kind
    )


def run_overstay_check(user=None):
    cfg = settings.SPS_SETTINGS
    now = timezone.now()
    grace = timedelta(minutes=cfg["OVERSTAY_GRACE_MINUTES"])
    warn = timedelta(minutes=cfg["EXPIRY_WARNING_MINUTES"])

    with transaction.atomic():
        qs = Reservation.objects.select_for_update().select_related("slot", "user")
        if user is not None:
            qs = qs.filter(user=user)

        # 1. "Parking expiring soon": once per reservation, only if the vehicle is inside
        for r in qs.filter(
            status="confirmed", actual_entry_time__isnull=False, actual_exit_time__isnull=True,
            expiry_warning_sent=False, end_time__gt=now, end_time__lte=now + warn,
        ):
            minutes_left = max(int((r.end_time - now).total_seconds() // 60), 1)
            notify(
                r.user, "Parking Expiring",
                f"Your parking at slot {r.slot.slot_number if r.slot else '-'} expires in {minutes_left} minutes.",
                kind="warning", reservation=r,
            )
            r.expiry_warning_sent = True
            r.save(update_fields=["expiry_warning_sent"])

        # 2. Vehicle still inside after end_time + grace -> OVERSTAY
        for r in qs.filter(
            status="confirmed", actual_entry_time__isnull=False, actual_exit_time__isnull=True,
            end_time__lt=now - grace,
        ):
            r.status = "overstay"
            r.save(update_fields=["status"])
            if r.slot:
                r.slot.status = "overstay"
                r.slot.save(update_fields=["status"])

        # 3. Refresh the single fine value + send the overstay alert once
        for r in qs.filter(status="overstay", actual_exit_time__isnull=True):
            r.overstay_minutes, r.fine_amount = r.calculate_overstay(now)
            fields = ["overstay_minutes", "fine_amount"]
            if not r.overstay_notified:
                notify(
                    r.user, "Overstay Detected",
                    f"Your parking time has expired. Current overstay: {r.overstay_minutes} minutes. "
                    f"Current fine: Rs. {r.fine_amount}.",
                    kind="danger", reservation=r,
                )
                r.overstay_notified = True
                fields.append("overstay_notified")
            r.save(update_fields=fields)

        # 4. No-show: paid booking whose window ended and the vehicle never arrived
        for r in qs.filter(status="confirmed", actual_entry_time__isnull=True, end_time__lt=now):
            r.status = "no_show"
            r.save(update_fields=["status"])
            if r.slot and r.slot.status == "reserved":
                r.slot.status = "available"
                r.slot.save(update_fields=["status"])
            notify(
                r.user, "Booking Missed",
                f"You did not check in for slot {r.slot.slot_number if r.slot else '-'} at {r.lot.name}. The slot was released.",
                kind="warning", reservation=r,
            )