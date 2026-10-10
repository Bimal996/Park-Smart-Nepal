from django.contrib import admin

from spsproject.admin_utils import SafeAdminMixin
from .models import ParkingLot, ParkingSlot


class ParkingSlotInline(admin.TabularInline):
    model = ParkingSlot
    extra = 0
    show_change_link = True


@admin.register(ParkingLot)
class ParkingLotAdmin(SafeAdminMixin, admin.ModelAdmin):
    list_display = ("name", "city", "address", "total_slots", "hourly_rate", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city", "address")
    ordering = ("name",)
    inlines = [ParkingSlotInline]


@admin.register(ParkingSlot)
class ParkingSlotAdmin(SafeAdminMixin, admin.ModelAdmin):
    list_display = ("slot_number", "lot", "slot_type", "status_badge")
    list_filter = ("lot", "slot_type", "status")
    search_fields = ("slot_number", "lot__name", "lot__city")
    ordering = ("lot", "slot_number")