from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import ContactMessage
from parking.models import ParkingLot
from reservations.models import Reservation


def home(request):
    """Public landing page. Logged-in users go straight to their dashboard."""
    if request.user.is_authenticated:
        return redirect("pages:dashboard")
    active = ParkingLot.objects.filter(is_active=True)
    stats = {
        "total_lots": active.count(),
        "total_cities": active.values("city").distinct().count(),
    }
    return render(request, "pages/home.html", {"featured_lots": active[:3], "stats": stats})

@login_required
def dashboard(request):
    lots = ParkingLot.objects.filter(is_active=True)[:3]
    reservations = Reservation.objects.filter(user=request.user).select_related("lot", "slot")[:5]
    stats = {
        "total_lots": ParkingLot.objects.filter(is_active=True).count(),
        "total_cities": ParkingLot.objects.filter(is_active=True).values("city").distinct().count(),
    }
    return render(request, "pages/dashboard.html", {"lots": lots, "reservations": reservations, "stats": stats})


def about(request):
    if request.user.is_authenticated:
        return redirect("pages:dashboard")
    team = [
        {
            "name": "Bimal Mahara",
            "role": "Solo Developer & BITM Student",
            "focus": "Designed and developed the full-stack ParkSmart Nepal system as a student of Sudur Paschimanchal Campus.",
        },
    ]
    milestones = [
        {"title": "Research & Planning", "detail": "Studied Dhangadhi parking pain points and drafted ER diagrams and DFDs for a Nepal-wide system."},
        {"title": "Core Build", "detail": "Implemented multi-app Django architecture with namespaced URLs and MySQL-ready models."},
        {"title": "Payments Integration", "detail": "Wired up eSewa, Khalti, and cash-on-arrival flows with live pricing."},
        {"title": "Polish & Viva Prep", "detail": "Refined the design system, tested edge cases, and prepared the walkthrough."},
    ]
    return render(request, "pages/about.html", {"team": team, "milestones": milestones})


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        if name and email and message:
            ContactMessage.objects.create(
                name=name[:120],
                email=email,
                message=message,
                user=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, "Thank you! Your message has been sent. We'll get back to you soon.")
        else:
            messages.error(request, "Please fill in all fields.")
        return redirect(request.path)  # prevents duplicate submits on refresh

    return render(request, "pages/contact.html")