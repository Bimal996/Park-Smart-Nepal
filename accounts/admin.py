from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User

from spsproject.admin_utils import SafeAdminMixin, install_dashboard_stats
from .models import UserProfile

# Upgrade the stock User admin
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class CustomUserAdmin(SafeAdminMixin, DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    date_hierarchy = "date_joined"


@admin.register(UserProfile)
class UserProfileAdmin(SafeAdminMixin, admin.ModelAdmin):
    list_display = ("user", "phone", "vehicle_number", "vehicle_type", "loyalty_points", "created_at")
    list_filter = ("vehicle_type", "created_at")
    search_fields = ("user__username", "user__email", "phone", "vehicle_number")
    ordering = ("-id",)


# Activates the dashboard KPI cards (keep this line at the bottom)
install_dashboard_stats()