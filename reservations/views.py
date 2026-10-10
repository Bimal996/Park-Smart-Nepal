from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from parking.models import ParkingLot, ParkingSlot

from .forms import ReservationForm
from .models import Notification, Reservation
from .services import notify, run_overstay_check


@login_required
def create_reservation(request, slug):
    lot = get_object_or_404(ParkingLot, slug=slug, is_active=True)
    slots = lot.slots.all().order_by("floor", "slot_number")

    if request.method == "POST":
        form = ReservationForm(request.POST, lot=lot)
        if form.is_valid():
            vehicle_type = form.cleaned_data["vehicle_type"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            selected_slot_number = form.cleaned_data["selected_slot"]

            hourly_rate = lot.rate_for(vehicle_type)
            duration_hours = max(1, round((end_time - start_time).total_seconds() / 3600))
            total_amount = hourly_rate * duration_hours

            with transaction.atomic():
                available_slot = lot.slots.select_for_update().filter(
                    slot_number=selected_slot_number,
                    status="available",
                ).first()
                if not available_slot:
                    form.add_error("selected_slot", "That parking slot was just taken. Choose another slot.")
                    return render(request, "reservations/create.html", {"lot": lot, "slots": slots, "form": form})

                reservation = form.save(commit=False)
                reservation.user = request.user
                reservation.lot = lot
                reservation.slot = available_slot
                reservation.hourly_rate = hourly_rate
                reservation.total_amount = total_amount
                reservation.save()

                available_slot.status = "reserved"
                available_slot.save(update_fields=["status"])

            messages.success(request, f"Slot {available_slot.slot_number} held for you. Complete payment to confirm.")
            return redirect("payments:choose", reference=reservation.reference)
    else:
        form = ReservationForm(lot=lot, initial={"selected_slot": request.GET.get("slot", "")})

    return render(request, "reservations/create.html", {"lot": lot, "slots": slots, "form": form})


@login_required
def my_bookings(request):
    run_overstay_check(user=request.user)  # keeps fines/alerts fresh even without a scheduler
    reservations = Reservation.objects.filter(user=request.user).select_related("lot", "slot")
    # The bell shows everything; this page only highlights the urgent ones.
    notifications = Notification.objects.filter(
        user=request.user, is_read=False, kind__in=["warning", "danger"]
    )[:5]
    return render(request, "reservations/my_bookings.html", {
        "reservations": reservations,
        "notifications": notifications,
    })


@login_required
def reservation_detail(request, reference):
    run_overstay_check(user=request.user)
    reservation = get_object_or_404(Reservation, reference=reference, user=request.user)
    return render(request, "reservations/detail.html", {"reservation": reservation})


@login_required
def cancel_reservation(request, reference):
    reservation = get_object_or_404(Reservation, reference=reference, user=request.user)
    if (
        request.method == "POST"
        and reservation.status in ("pending_payment", "confirmed")
        and not reservation.actual_entry_time
    ):
        reservation.status = "cancelled"
        reservation.save(update_fields=["status"])
        if reservation.slot:
            reservation.slot.status = "available"
            reservation.slot.save(update_fields=["status"])
        notify(request.user, "Booking Cancelled", f"Reservation {reservation.reference} has been cancelled.", kind="info", reservation=reservation)
        messages.success(request, f"Reservation {reservation.reference} has been cancelled.")
    return redirect("reservations:my_bookings")


# ---------------------------------------------------------------------------
# Slot lifecycle: check-in, exit, pay fine, dismiss alerts
# ---------------------------------------------------------------------------
@login_required
@require_POST
def check_in(request, reference):
    """RESERVED -> OCCUPIED (driver has arrived)."""
    with transaction.atomic():
        reservation = get_object_or_404(
            Reservation.objects.select_for_update(), reference=reference, user=request.user
        )
        if not reservation.can_check_in:
            messages.error(request, "You can't check in to this booking right now.")
            return redirect("reservations:detail", reference=reference)

        reservation.actual_entry_time = timezone.now()
        reservation.save(update_fields=["actual_entry_time"])
        if reservation.slot:
            reservation.slot.status = "occupied"
            reservation.slot.save(update_fields=["status"])

    notify(
        request.user, "Checked In",
        f"You checked in at slot {reservation.slot.slot_number}. Please exit before {timezone.localtime(reservation.end_time):%I:%M %p}.",
        kind="success", reservation=reservation,
    )
    messages.success(request, f"Checked in. Slot {reservation.slot.slot_number} is now occupied.")
    return redirect("reservations:detail", reference=reference)


@login_required
@require_POST
def exit_parking(request, reference):
    """OCCUPIED / OVERSTAY -> COMPLETED, slot -> AVAILABLE, final fine locked in."""
    with transaction.atomic():
        reservation = get_object_or_404(
            Reservation.objects.select_for_update(), reference=reference, user=request.user
        )
        if not reservation.is_in_use:
            messages.error(request, "This booking is not currently in use.")
            return redirect("reservations:detail", reference=reference)

        now = timezone.now()
        reservation.actual_exit_time = now
        reservation.overstay_minutes, reservation.fine_amount = reservation.calculate_overstay(now)
        reservation.status = "completed"
        reservation.save()

        if reservation.slot:
            reservation.slot.status = "available"   # immediately bookable by someone else
            reservation.slot.save(update_fields=["status"])

    if reservation.fine_due:
        notify(
            request.user, "Fine Due",
            f"You exited with an overstay of {reservation.overstay_minutes} minutes. Final fine: Rs. {reservation.fine_amount}.",
            kind="danger", reservation=reservation,
        )
        messages.warning(request, f"You have exited. Final overstay fine: Rs. {reservation.fine_amount}. Please pay it.")
    else:
        notify(request.user, "Parking Completed", "You have exited. Thank you for parking with us!", kind="success", reservation=reservation)
        messages.success(request, "You have exited. The slot is available again. Thank you!")
    return redirect("reservations:detail", reference=reference)


@login_required
def pay_fine(request, reference):
    """Demo fine payment screen. Wire eSewa/Khalti here later if you want."""
    reservation = get_object_or_404(Reservation, reference=reference, user=request.user)

    # While the car is still inside, refresh the live fine first.
    if reservation.status == "overstay":
        reservation.overstay_minutes, reservation.fine_amount = reservation.calculate_overstay()

    if reservation.fine_amount <= 0 or reservation.fine_paid:
        messages.info(request, "There is no fine to pay for this booking.")
        return redirect("reservations:detail", reference=reference)

    if request.method == "POST":
        reservation.fine_paid = True
        reservation.fine_paid_at = timezone.now()
        reservation.save(update_fields=["fine_amount", "overstay_minutes", "fine_paid", "fine_paid_at"])
        notify(request.user, "Fine Paid", f"Your overstay fine of Rs. {reservation.fine_amount} was paid. Thank you!", kind="success", reservation=reservation)
        messages.success(request, f"Fine of Rs. {reservation.fine_amount} paid. Thank you!")
        return redirect("reservations:detail", reference=reference)

    return render(request, "reservations/pay_fine.html", {"reservation": reservation})


@login_required
@require_POST
def dismiss_notification(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect("reservations:my_bookings")


# ---------------------------------------------------------------------------
# Navbar notification bell
# ---------------------------------------------------------------------------
@login_required
def notification_feed(request):
    """JSON used by the bell to refresh itself every 30 seconds without a page reload."""
    run_overstay_check(user=request.user)
    qs = Notification.objects.filter(user=request.user)
    return JsonResponse({
        "unread": qs.filter(is_read=False).count(),
        "items": [
            {
                "id": n.pk,
                "title": n.title,
                "message": n.message,
                "kind": n.kind,
                "is_read": n.is_read,
                "time": n.time_ago,
                "url": reverse("reservations:notification_open", args=[n.pk]),
            }
            for n in qs[:8]
        ],
    })


@login_required
def notification_open(request, pk):
    """Mark one notification read, then jump to the booking it is about."""
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    if n.reservation_id:
        return redirect("reservations:detail", reference=n.reservation.reference)
    return redirect("reservations:my_bookings")


@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect(request.META.get("HTTP_REFERER") or "reservations:my_bookings")