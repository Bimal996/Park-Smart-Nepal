from django.contrib import admin
from django.utils.html import format_html

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("status_badge", "name", "email", "short_message", "user", "created_at")
    list_display_links = ("name", "short_message")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "message")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    actions = None  # no bulk delete or other actions

    # ---------- READ-ONLY: view permission only ----------
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # With only "view" allowed, Django shows every field as read-only.

    # ---------- Mark as read when an admin opens it ----------
    def change_view(self, request, object_id, form_url="", extra_context=None):
        ContactMessage.objects.filter(pk=object_id, is_read=False).update(is_read=True)
        return super().change_view(request, object_id, form_url, extra_context)

    # ---------- Columns ----------
    @admin.display(description="Status", ordering="is_read")
    def status_badge(self, obj):
        if obj.is_read:
            return format_html('<span class="sps-badge sps-gray">Read</span>')
        return format_html('<span class="sps-badge sps-amber">New</span>')

    @admin.display(description="Message")
    def short_message(self, obj):
        text = obj.message.replace("\n", " ")
        return text[:70] + ("..." if len(text) > 70 else "")