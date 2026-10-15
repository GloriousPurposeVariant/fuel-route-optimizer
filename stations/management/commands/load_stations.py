from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stations.fuel_csv import DEFAULT_CSV, read_us_stations
from stations.geocoding import coordinate_lookup
from stations.models import City, FuelStation
from stations.normalize import city_key


class Command(BaseCommand):
    help = "Clean the fuel price CSV and load US stations with coordinates."

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to the fuel prices CSV.")

    def handle(self, *args, **options):
        csv_path = settings.BASE_DIR / options["csv"]
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")
        if not City.objects.exists():
            raise CommandError("City table is empty. Run `python manage.py load_cities` first.")

        parsed = read_us_stations(csv_path)
        coords = coordinate_lookup()

        stations = []
        unmatched = Counter()
        for opis_id, row in parsed.stations.items():
            point = coords.get((city_key(row["City"]), row["State"]))
            if point is None:
                unmatched[f"{row['City']}, {row['State']}"] += 1
                continue
            stations.append(FuelStation(
                opis_id=opis_id,
                name=row["Truckstop Name"],
                address=row["Address"],
                city=row["City"],
                state=row["State"],
                rack_id=int(row["Rack ID"]),
                price=row["price"],
                latitude=point[0],
                longitude=point[1],
            ))

        with transaction.atomic():
            FuelStation.objects.all().delete()
            FuelStation.objects.bulk_create(stations, batch_size=1000)

        self.stdout.write(f"Rows read:                  {parsed.total_rows:,}")
        self.stdout.write(f"Dropped non-US rows:        {parsed.non_us_rows:,}")
        self.stdout.write(f"Dropped duplicate rows:     {parsed.duplicate_rows:,} (kept cheapest price per station)")
        self.stdout.write(f"Unique US stations:         {len(parsed.stations):,}")
        if unmatched:
            self.stdout.write(self.style.WARNING(
                f"Skipped, city not found:    {sum(unmatched.values()):,} in {len(unmatched):,} places"
            ))
            for place, count in unmatched.most_common(15):
                self.stdout.write(f"    {place} ({count})")
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(stations):,} fuel stations."))
