import csv
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from stations.fuel_csv import DEFAULT_CSV, read_us_stations
from stations.geocoding import (
    OVERRIDE_FIELDS,
    OVERRIDES_PATH,
    coordinate_lookup,
    read_override_rows,
)
from stations.models import City
from stations.normalize import city_key

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
REQUEST_INTERVAL_SECONDS = 1.1
REJECTED_TYPES = {"country", "state", "region", "county"}


class Command(BaseCommand):
    help = "One-time: geocode station cities missing from the Census data via Nominatim, and save them to data/city_overrides.csv."

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to the fuel prices CSV.")

    def handle(self, *args, **options):
        csv_path = settings.BASE_DIR / options["csv"]
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")
        if not City.objects.exists():
            raise CommandError("City table is empty. Run `python manage.py load_cities` first.")

        coords = coordinate_lookup()
        missing = sorted(
            {
                (row["City"], row["State"])
                for row in read_us_stations(csv_path).stations.values()
                if (city_key(row["City"]), row["State"]) not in coords
            }
        )
        if not missing:
            self.stdout.write(self.style.SUCCESS("Every station city already has coordinates."))
            return

        self.stdout.write(
            f"Geocoding {len(missing)} places via Nominatim (~{len(missing) * REQUEST_INTERVAL_SECONDS:.0f}s)..."
        )
        session = requests.Session()
        session.headers["User-Agent"] = settings.NOMINATIM_USER_AGENT

        found, not_found = [], []
        for index, (city, state) in enumerate(missing):
            if index:
                time.sleep(REQUEST_INTERVAL_SECONDS)
            point = self._geocode(session, city, state)
            if point:
                found.append({"city": city, "state": state, "lat": point[0], "lon": point[1]})
            else:
                not_found.append(f"{city}, {state}")

        rows = read_override_rows() + found
        rows.sort(key=lambda r: (r["state"], r["city"]))
        with open(OVERRIDES_PATH, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=OVERRIDE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(f"Added {len(found)} places to {OVERRIDES_PATH.name}.")
        )
        if not_found:
            self.stdout.write(
                self.style.WARNING(
                    f"No town-level match for {len(not_found)} places (add them by hand):"
                )
            )
            for place in not_found:
                self.stdout.write(f"    {place}")

    @staticmethod
    def _geocode(session, city, state):
        response = session.get(
            NOMINATIM_URL,
            params={
                "q": f"{city}, {state}, USA",
                "format": "jsonv2",
                "countrycodes": "us",
                "addressdetails": 1,
                "limit": 10,
            },
            timeout=10,
        )
        response.raise_for_status()
        for result in response.json():
            in_state = result.get("address", {}).get("ISO3166-2-lvl4") == f"US-{state}"
            if in_state and result.get("addresstype") not in REJECTED_TYPES:
                return round(float(result["lat"]), 6), round(float(result["lon"]), 6)
        return None
