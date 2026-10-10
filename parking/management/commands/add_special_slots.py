from django.core.management.base import BaseCommand

from parking.models import ParkingLot, ParkingSlot


class Command(BaseCommand):
    help = (
        "Adds dedicated emergency and/or VIP slots to existing parking lots. "
        "Safe to run more than once — it skips a slot number that already exists "
        "in a lot instead of creating a duplicate."
    )

    def add_arguments(self, parser):
        parser.add_argument("--lot", type=str, default=None,
            help="Slug of a single lot to update. Omit to update every active lot.")
        parser.add_argument("--emergency", type=int, default=1,
            help="How many emergency slots to add per lot (default: 1).")
        parser.add_argument("--vip", type=int, default=1,
            help="How many VIP slots to add per lot (default: 1).")
        parser.add_argument("--vehicle-type", type=str, default="car",
            choices=[c[0] for c in ParkingSlot.VEHICLE_CHOICES],
            help="Vehicle type these special slots are sized for (default: car).")
        parser.add_argument("--floor", type=str, default="Ground",
            help="Floor label to store on the new slots (default: Ground).")

    def handle(self, *args, **options):
        lots = ParkingLot.objects.filter(is_active=True)
        if options["lot"]:
            lots = lots.filter(slug=options["lot"])
            if not lots.exists():
                self.stderr.write(self.style.ERROR(f"No active lot found with slug '{options['lot']}'."))
                return

        created_count = 0
        skipped_count = 0

        for lot in lots:
            created_count_this_lot = 0

            for i in range(1, options["emergency"] + 1):
                slot_number = f"EMG{i}"
                _, created = ParkingSlot.objects.get_or_create(
                    lot=lot, slot_number=slot_number,
                    defaults={
                        "vehicle_type": options["vehicle_type"],
                        "floor": options["floor"],
                        "status": "available",
                        "slot_type": "emergency",
                    },
                )
                created_count += created
                created_count_this_lot += created
                skipped_count += not created

            for i in range(1, options["vip"] + 1):
                slot_number = f"VIP{i}"
                _, created = ParkingSlot.objects.get_or_create(
                    lot=lot, slot_number=slot_number,
                    defaults={
                        "vehicle_type": options["vehicle_type"],
                        "floor": options["floor"],
                        "status": "available",
                        "slot_type": "vip",
                    },
                )
                created_count += created
                created_count_this_lot += created
                skipped_count += not created

            self.stdout.write(f"  {lot.name}: +{created_count_this_lot} new special slot(s)")

        self.stdout.write(self.style.SUCCESS(
            f"Done — {created_count} slot(s) created, {skipped_count} already existed and were skipped."
        ))