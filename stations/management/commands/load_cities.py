import csv
import io
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stations.constants import US_STATES
from stations.models import City
from stations.normalize import census_aliases, city_key, strip_census_suffix

GAZETTEER_FILES = ["2025_Gaz_place_national.zip", "2025_Gaz_cousubs_national.zip"]


class Command(BaseCommand):
    help = "Load US places from the Census Gazetteer into the City table for offline geocoding."

    def handle(self, *args, **options):
        cities = {}
        aliases = {}
        for filename in GAZETTEER_FILES:
            path = settings.BASE_DIR / "data" / filename
            if not path.exists():
                raise CommandError(f"Missing {path}. Download it first (see README).")
            for row in self._read_gazetteer(path):
                state = row["USPS"]
                if state not in US_STATES:
                    continue
                name = strip_census_suffix(row["NAME"])
                value = (name, float(row["INTPTLAT"]), float(row["INTPTLONG"]))
                cities.setdefault((city_key(name), state), value)
                for alias in census_aliases(name):
                    aliases.setdefault((city_key(alias), state), value)

        for key, value in aliases.items():
            cities.setdefault(key, value)

        objects = [
            City(key=key, state=state, name=name, latitude=lat, longitude=lon)
            for (key, state), (name, lat, lon) in cities.items()
        ]
        with transaction.atomic():
            City.objects.all().delete()
            City.objects.bulk_create(objects, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(objects):,} city keys."))

    @staticmethod
    def _read_gazetteer(path):
        with zipfile.ZipFile(path) as archive:
            with archive.open(archive.namelist()[0]) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="|")
                for row in reader:
                    yield {k.strip(): v.strip() for k, v in row.items()}
