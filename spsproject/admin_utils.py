import csv

from django.apps import apps
from django.contrib import admin
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

# ---------------------------------------------------------------
# Status badges
# ---------------------------------------------------------------
_GREEN = {"success", "paid", "completed", "complete", "active", "available", "confirmed", "approved", "done"}
_AMBER = {"pending", "reserved", "booked", "initiated", "processing", "upcoming"}
_RED = {"failed", "cancelled", "canceled", "expired", "overstay", "overstayed", "rejected", "maintenance"}
_BLUE = {"occupied", "in_use", "checked_in", "ongoing", "parked"}


def status_badge(raw_value, label=None):
    key = str(raw_value or "").strip().lower().replace(" ", "_")
    if key in _GREEN:
        color = "green"
    elif key in _AMBER:
        color = "amber"
    elif key in _RED:
        color = "red"
    elif key in _BLUE:
        color = "blue"
    else:
        color = "gray"
    return format_html('<span class="sps-badge sps-{}">{}</span>', color, label or raw_value or "—")


# ---------------------------------------------------------------
# Mixin: safe against wrong field names + common features
# ---------------------------------------------------------------
class SafeAdminMixin:
    """Removes any list_display / list_filter / search / readonly / ordering
    entry that is not a real field or attribute. Cleaning happens in __init__
    so it runs BEFORE Django's admin system checks."""

    list_per_page = 25
    save_on_top = True
    actions = ["export_as_csv"]

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.list_display = self._clean(self.list_display) or ("__str__",)
        self.list_filter = self._clean(self.list_filter)
        self.search_fields = self._clean(self.search_fields)
        self.readonly_fields = self._clean(self.readonly_fields)
        self.ordering = self._clean(self.ordering) or None
        if self.date_hierarchy and not self._ok(self.date_hierarchy):
            self.date_hierarchy = None

    def _clean(self, items):
        return tuple(i for i in (items or ()) if self._ok(i))

    def _ok(self, name):
        if callable(name):
            return True
        if isinstance(name, (tuple, list)):
            name = name[0]
        if not isinstance(name, str):
            return True
        if name == "__str__":
            return True
        base = name.lstrip("^=@-").split("__")[0]
        if hasattr(self, base) or hasattr(self.model, base):
            return True
        try:
            self.model._meta.get_field(base)
            return True
        except FieldDoesNotExist:
            return False

    @admin.action(description="Export selected to CSV")
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        fields = list(meta.fields)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{meta.model_name}_export.csv"'
        writer = csv.writer(response)
        writer.writerow([f.name for f in fields])
        for obj in queryset:
            writer.writerow([str(getattr(obj, f.name, "")) for f in fields])
        return response

    # Reusable status column (shows "-" if the model has no `status`)
    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        raw = getattr(obj, "status", "")
        label = obj.get_status_display() if hasattr(obj, "get_status_display") else raw
        return status_badge(raw, label)


# ---------------------------------------------------------------
# Dashboard stats (shown on the admin home page)
# ---------------------------------------------------------------
def _model(app_label, name):
    try:
        return apps.get_model(app_label, name)
    except LookupError:
        return None


def _safe(fn, default=0):
    try:
        return fn() or default
    except Exception:
        return default


def get_dashboard_stats():
    User = _model("auth", "User")
    Lot = _model("parking", "ParkingLot")
    Slot = _model("parking", "ParkingSlot")
    Reservation = _model("reservations", "Reservation")
    Payment = _model("payments", "Payment")
    today = timezone.localdate()

    paid = Payment.objects.filter(status="success") if Payment else None
    return {
        "users": _safe(lambda: User.objects.count()),
        "lots": _safe(lambda: Lot.objects.count()),
        "slots": _safe(lambda: Slot.objects.count()),
        "reservations": _safe(lambda: Reservation.objects.count()),
        "reservations_today": _safe(lambda: Reservation.objects.filter(created_at__date=today).count()),
        "payments_ok": _safe(lambda: paid.count()),
        "revenue": _safe(lambda: paid.aggregate(t=Sum("amount"))["t"]),
    }


def install_dashboard_stats():
    """Injects `sps_stats` into the admin index page context."""
    if getattr(admin.site, "_sps_patched", False):
        return
    original_index = admin.site.index

    def index(request, extra_context=None):
        extra = dict(extra_context or {})
        extra["sps_stats"] = get_dashboard_stats()
        return original_index(request, extra)

    admin.site.index = index
    admin.site._sps_patched = True