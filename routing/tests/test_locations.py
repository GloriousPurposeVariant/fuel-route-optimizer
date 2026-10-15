from django.test import TestCase

from routing.exceptions import (
    InvalidLocation,
    LocationNotFound,
    LocationNotInUSA,
    UnsupportedRegion,
)
from routing.locations import resolve_location
from stations.models import City


class ResolveLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        City.objects.create(
            name="St. Louis", state="MO", key="stlouis", latitude=38.63, longitude=-90.24
        )

    def test_resolves_alternate_spelling_and_lowercase_state(self):
        location = resolve_location("Saint Louis, mo")
        self.assertEqual(location.name, "St. Louis, MO")
        self.assertAlmostEqual(location.latitude, 38.63)

    def test_rejects_non_us_state(self):
        with self.assertRaises(LocationNotInUSA):
            resolve_location("Toronto, ON")

    def test_rejects_bad_format(self):
        for query in ["Dallas", "", "Paris, France", ", TX"]:
            with self.subTest(query=query), self.assertRaises(InvalidLocation):
                resolve_location(query)

    def test_unknown_city(self):
        with self.assertRaises(LocationNotFound):
            resolve_location("Atlantis, TX")

    def test_rejects_alaska_and_hawaii(self):
        for query in ["Anchorage, AK", "Honolulu, HI"]:
            with self.subTest(query=query), self.assertRaises(UnsupportedRegion):
                resolve_location(query)
