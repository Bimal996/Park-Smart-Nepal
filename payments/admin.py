from django.contrib import admin

from spsproject.admin_utils import SafeAdminMixin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(SafeAdminMixin, admin.ModelAdmin):
    list_display = ("reference", "reservation", "method", "amount", "status_badge", "paid_at", "created_at")
    list_filter = ("status", "method", "created_at", "paid_at")
    search_fields = ("transaction_uuid", "reference", "reservation__reference", "reservation__user__username")
    date_hierarchy = "created_at"
    ordering = ("-id",)
    readonly_fields = ("created_at",)