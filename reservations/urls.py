from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("book/<slug:slug>/", views.create_reservation, name="create"),
    path("mine/", views.my_bookings, name="my_bookings"),
    path("notifications/feed/", views.notification_feed, name="notification_feed"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification_open"),
    path("notifications/<int:pk>/dismiss/", views.dismiss_notification, name="dismiss_notification"),
    path("<str:reference>/", views.reservation_detail, name="detail"),
    path("<str:reference>/cancel/", views.cancel_reservation, name="cancel"),
    path("<str:reference>/check-in/", views.check_in, name="check_in"),
    path("<str:reference>/exit/", views.exit_parking, name="exit_parking"),
    path("<str:reference>/pay-fine/", views.pay_fine, name="pay_fine"),
]