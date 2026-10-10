"""
Django settings for the Smart Parking System (SPS) project.

Built for a BITM university viva project targeting Nepal's parking
market, starting in Dhangadhi. Runs on SQLite out of the box with zero
setup; flip USE_MYSQL to True (or set env vars) to switch to MySQL.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------
# Core / security
# --------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-sps-dev-key-change-this-in-production-8x!2f",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# --------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Smart Parking System apps
    "accounts",
    "pages",
    "parking",
    "reservations",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "spsproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pages.context_processors.site_settings",
                "reservations.context_processors.notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "spsproject.wsgi.application"

# --------------------------------------------------------------------
# Database
#
# Defaults to SQLite so the project runs immediately with no external
# services. Set USE_MYSQL=True as an environment variable (and fill in
# the DB_* variables) to switch to MySQL for the deployed/viva version.
# --------------------------------------------------------------------
USE_MYSQL = os.environ.get("USE_MYSQL", "False") == "True"

if USE_MYSQL:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "smart_parking_db"),
            "USER": os.environ.get("DB_USER", "root"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------
# Static & media files
# --------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------
# Auth redirects
# --------------------------------------------------------------------
LOGIN_REDIRECT_URL = "pages:dashboard"
LOGOUT_REDIRECT_URL = "pages:home"

# --------------------------------------------------------------------
# Smart Parking System - business configuration
# --------------------------------------------------------------------
SPS_SETTINGS = {
    "SITE_NAME": "ParkSmart Nepal",
    "SITE_URL": "https://bimal.pythonanywhere.com",
    "SITE_TAGLINE": "Smart Parking System",
    "SUPPORT_PHONE": "+977-61-123456",
    "SUPPORT_PHONE_ALT": "+977-9800000000",
    "SUPPORT_EMAIL": "support@parksmart.com.np",
    "SUPPORT_ADDRESS": "Dhangadhi, Kailali, Nepal",
    "SOCIAL_FACEBOOK": "https://www.facebook.com/share/14paPrThU69/",
    "SOCIAL_INSTAGRAM": "https://instagram.com/parksmartnepal",
    "SOCIAL_TWITTER": "https://twitter.com/parksmartnepal",
    "SOCIAL_LINKEDIN": "https://linkedin.com/company/parksmartnepal",
    "GOOGLE_MAPS_API_KEY": os.environ.get("GOOGLE_MAPS_API_KEY", "AIzaSyAKQo4yx2Fnn4XnCVxej7t5N2eZ8-QAeUE"),
    "ESEWA_MERCHANT_CODE": os.environ.get("ESEWA_MERCHANT_CODE", "EPAYTEST"),
    "ESEWA_SUCCESS_URL": os.environ.get("ESEWA_SUCCESS_URL", ""),
    "ESEWA_FAILURE_URL": os.environ.get("ESEWA_FAILURE_URL", ""),
    "KHALTI_PUBLIC_KEY": os.environ.get("KHALTI_PUBLIC_KEY", ""),
    "KHALTI_SECRET_KEY": os.environ.get("KHALTI_SECRET_KEY", ""),
    "ESEWA_PRODUCT_CODE": "EPAYTEST",
    "ESEWA_SECRET_KEY": "8gBm/:&EnhH.1/q(",
    "CURRENCY_SYMBOL": "Rs.",
    "HOURLY_RATE_DEFAULT": 40,  # NPR per hour, fallback if a lot has none set
    # Overstay / fine rules (change these numbers any time)
    "OVERSTAY_GRACE_MINUTES": 10,          # free minutes after the booking ends
    "OVERSTAY_FINE_AMOUNT": 20,            # Rs. charged per fine block
    "OVERSTAY_FINE_INTERVAL_MINUTES": 30,  # length of one fine block
    "EXPIRY_WARNING_MINUTES": 15,          # "parking expiring soon" alert
    "CHECKIN_EARLY_MINUTES": 15,           # how early a user may check in
}

MESSAGE_TAGS = {
    10: "info",
    20: "info",
    25: "success",
    30: "warning",
    40: "danger",
}

# ---------------------------------------------------------------
# ADMIN PORTAL (Jazzmin)
# ---------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "ParkSmart Admin",
    "site_header": "ParkSmart Nepal",
    "site_brand": "ParkSmart",
    "welcome_sign": "Welcome to ParkSmart Control Center",
    "copyright": "ParkSmart Nepal",

    # Global search box (top bar)
    "search_model": ["auth.User", "reservations.Reservation", "payments.Payment"],

    # Top navigation
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Site", "url": "/", "new_window": True},
        {"model": "reservations.Reservation"},
        {"model": "payments.Payment"},
    ],
    "usermenu_links": [
        {"name": "View Site", "url": "/", "new_window": True, "icon": "fas fa-globe"},
        {"model": "auth.user"},
    ],

    # Sidebar
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": [
        "reservations", "reservations.reservation", "reservations.notification",
        "payments", "payments.payment",
        "parking", "parking.parkinglot", "parking.parkingslot",
        "accounts", "accounts.userprofile",
        "auth",
    ],

    # Icons (FontAwesome 5)
    "icons": {
        "auth": "fas fa-shield-alt",
        "auth.user": "fas fa-users",
        "auth.Group": "fas fa-users-cog",
        "accounts": "fas fa-id-card",
        "accounts.userprofile": "fas fa-user-circle",
        "parking": "fas fa-parking",
        "parking.parkinglot": "fas fa-warehouse",
        "parking.parkingslot": "fas fa-car",
        "reservations": "fas fa-calendar-check",
        "reservations.reservation": "fas fa-clipboard-list",
        "reservations.notification": "fas fa-bell",
        "payments": "fas fa-wallet",
        "payments.payment": "fas fa-credit-card",
        "pages": "fas fa-globe",
        "pages.contactmessage": "fas fa-envelope",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",

    # Forms
    "related_modal_active": True,          # add/edit related objects in a popup
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
    "show_ui_builder": False,
    "custom_css": "css/sps_admin.css",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-warning",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-warning",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": "darkly",           # gives you a light/dark toggle
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}