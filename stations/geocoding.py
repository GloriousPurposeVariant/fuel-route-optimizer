import csv
from functools import lru_cache

from django.conf import settings

from .models import City
from .normalize import city_key

OVERRIDES_PATH = settings.BASE_DIR / "data" / "city_overrides.csv"
OVERRIDE_FIELDS = ["city", "state", "lat", "lon"]


def read_override_rows():
    if not OVERRIDES_PATH.exists():
        return []
    with open(OVERRIDES_PATH, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def coordinate_lookup():
    """Map (city_key, state) to (lat, lon): Census cities first, manual overrides as fallback."""
    coords = {
        (key, state): (lat, lon)
        for key, state, lat, lon in City.objects.values_list(
            "key", "state", "latitude", "longitude"
        )
    }
    for row in read_override_rows():
        coords.setdefault(
            (city_key(row["city"]), row["state"]),
            (float(row["lat"]), float(row["lon"])),
        )
    return coords


def find_city(name, state):
    """Return (name, lat, lon) for one city, or None. Census first, overrides second."""
    key = city_key(name)
    row = (
        City.objects.filter(key=key, state=state)
        .values_list("name", "latitude", "longitude")
        .first()
    )
    if row:
        return row
    return _override_index().get((key, state))


@lru_cache(maxsize=1)
def _override_index():
    return {
        (city_key(r["city"]), r["state"]): (r["city"], float(r["lat"]), float(r["lon"]))
        for r in read_override_rows()
    }
