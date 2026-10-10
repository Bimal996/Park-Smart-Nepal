import time

from django.core.management.base import BaseCommand

from reservations.services import run_overstay_check


class Command(BaseCommand):
    help = "Detect expiring bookings, overstays, no-shows and update fines."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep running (good for the viva demo).")
        parser.add_argument("--interval", type=int, default=60, help="Seconds between checks when using --loop.")

    def handle(self, *args, **opts):
        if opts["loop"]:
            self.stdout.write(f"Checking every {opts['interval']}s. Press Ctrl+C to stop.")
            try:
                while True:
                    run_overstay_check()
                    self.stdout.write("check complete")
                    time.sleep(opts["interval"])
            except KeyboardInterrupt:
                self.stdout.write("Stopped.")
        else:
            run_overstay_check()
            self.stdout.write(self.style.SUCCESS("Overstay check complete."))