from django.contrib import admin

from spsproject.admin_utils import SafeAdminMixin
from .models import Notification, Reservation


@admin.register(Reservation)
class ReservationAdmin(SafeAdminMixin, admin.ModelAdmin):
    list_display = ("reference", "user", "slot", "vehicle_number", "start_time", "end_time",
                    "total_amount", "status_badge", "created_at")
    list_filter = ("status", "created_at", "start_time")
    search_fields = ("reference", "user__username", "user__email", "vehicle_number", "slot__slot_number")
    date_hierarchy = "created_at"
    ordering = ("-id",)
    readonly_fields = ("created_at",)


@admin.register(Notification)
class NotificationAdmin(SafeAdminMixin, admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "title", "message")
    ordering = ("-id",)