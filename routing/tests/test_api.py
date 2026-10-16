from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from routing.corridor import clear_station_index
from routing.exceptions import RoutingUnavailable
from routing.ors import Route
from stations.models import City, FuelStation

FAKE_ROUTE = Route(
    coordinates=[[-100.0, 35.0], [-99.0, 35.0]], distance_miles=56.7, duration_hours=1.0
)


class RouteApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        City.objects.create(name="Alpha", state="TX", key="alpha", latitude=35.0, longitude=-100.0)
        City.objects.create(name="Beta", state="TX", key="beta", latitude=35.0, longitude=-99.0)
        for opis_id, lon, price in [(1, -99.9, "3.00"), (2, -99.5, "2.50")]:
            FuelStation.objects.create(
                opis_id=opis_id,
                name=f"Stop {opis_id}",
                address="I-40",
                city="Alpha",
                state="TX",
                rack_id=1,
                price=price,
                latitude=35.0,
                longitude=lon,
            )

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("route")
        clear_station_index()
        cache.clear()

    @mock.patch("routing.services.get_route", return_value=FAKE_ROUTE)
    def test_returns_plan_with_one_routing_call(self, get_route):
        response = self.client.get(self.url, {"start": "Alpha, TX", "finish": "Beta, TX"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(get_route.call_count, 1)
        self.assertEqual([stop["opis_id"] for stop in body["fuel_stops"]], [1, 2])
        self.assertAlmostEqual(body["summary"]["total_gallons"], 5.67, places=2)
        self.assertAlmostEqual(
            body["summary"]["total_fuel_cost_usd"],
            sum(s["cost_usd"] for s in body["fuel_stops"]),
            places=2,
        )
        self.assertEqual(body["route_geometry"]["type"], "LineString")
        self.assertIn("/map/?start=Alpha%2C+TX&finish=Beta%2C+TX", body["map_url"])

    def test_missing_parameter(self):
        response = self.client.get(self.url, {"start": "Alpha, TX"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "MISSING_PARAMETER")

    @mock.patch("routing.services.get_route")
    def test_non_us_location_never_calls_ors(self, get_route):
        response = self.client.get(self.url, {"start": "Toronto, ON", "finish": "Beta, TX"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "LOCATION_NOT_IN_USA")
        get_route.assert_not_called()

    @mock.patch("routing.services.get_route", side_effect=RoutingUnavailable())
    def test_routing_outage_is_503(self, get_route):
        response = self.client.get(self.url, {"start": "Alpha, TX", "finish": "Beta, TX"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "ROUTING_UNAVAILABLE")

    @mock.patch("routing.services.get_route")
    def test_same_start_and_finish_skips_routing(self, get_route):
        response = self.client.get(self.url, {"start": "Alpha, TX", "finish": "alpha, tx"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["total_fuel_cost_usd"], 0.0)
        get_route.assert_not_called()

    @mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"route": "2/minute"})
    @mock.patch("routing.services.get_route", return_value=FAKE_ROUTE)
    def test_rate_limit_returns_429(self, get_route):
        params = {"start": "Alpha, TX", "finish": "Beta, TX"}
        for _ in range(2):
            self.assertEqual(self.client.get(self.url, params).status_code, 200)
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "RATE_LIMITED")

    @mock.patch("routing.services.get_route", return_value=FAKE_ROUTE)
    def test_repeated_trip_is_served_from_route_cache(self, get_route):
        params = {"start": "Alpha, TX", "finish": "Beta, TX"}
        first = self.client.get(self.url, params)
        second = self.client.get(self.url, {"start": "alpha, tx", "finish": "Beta, TX"})
        self.assertEqual(get_route.call_count, 1)
        self.assertEqual(first["X-Route-Cache"], "MISS")
        self.assertEqual(second["X-Route-Cache"], "HIT")
        self.assertEqual(first.json()["summary"], second.json()["summary"])

    @mock.patch("routing.services.get_route", return_value=FAKE_ROUTE)
    def test_timing_headers(self, get_route):
        response = self.client.get(self.url, {"start": "Alpha, TX", "finish": "Beta, TX"})
        self.assertIn("route;dur=", response["Server-Timing"])
        self.assertIn("optimize;dur=", response["Server-Timing"])
        self.assertGreater(float(response["X-Response-Time-ms"]), 0)
