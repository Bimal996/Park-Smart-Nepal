import time

from .models import Notification
from .services import run_overstay_check

CHECK_EVERY_SECONDS = 30


def notifications(request):
    """Gives every page the navbar bell data: nav_unread_count + nav_notifications."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or request.path.startswith("/admin/"):
        return {}

    # Refresh expiring / overstay / fine state at most once every 30 s per session,
    # so alerts appear on ANY page without needing a scheduler.
    session = getattr(request, "session", None)
    if session is not None:
        now = time.time()
        if now - session.get("sps_overstay_check_ts", 0) > CHECK_EVERY_SECONDS:
            try:
                run_overstay_check(user=user)
            except Exception:  # never break a page because of the bell
                pass
            session["sps_overstay_check_ts"] = now

    qs = Notification.objects.filter(user=user)
    return {
        "nav_unread_count": qs.filter(is_read=False).count(),
        "nav_notifications": list(qs[:8]),
    }