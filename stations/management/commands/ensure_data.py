from django.core.management import call_command
from django.core.management.base import BaseCommand

from stations.models import City, FuelStation


class Command(BaseCommand):
    help = (
        "Load cities and stations only if their tables are empty (used when the container starts)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Reload even if data already exists."
        )

    def handle(self, *args, **options):
        force = options["force"]

        if force or not City.objects.exists():
            call_command("load_cities", stdout=self.stdout)
        else:
            self.stdout.write(f"Cities already loaded ({City.objects.count():,}); skipping.")

        if force or not FuelStation.objects.exists():
            call_command("load_stations", stdout=self.stdout)
        else:
            self.stdout.write(
                f"Stations already loaded ({FuelStation.objects.count():,}); skipping."
            )
