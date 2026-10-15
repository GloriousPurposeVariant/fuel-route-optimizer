from django.test import SimpleTestCase

from routing.corridor import CorridorStation
from routing.exceptions import FuelGap
from routing.optimizer import plan_fuel_stops

RANGE = 500
MPG = 10


def station(station_id, mile, price):
    return CorridorStation(
        station_id=station_id, mile_marker=mile, distance_from_route_miles=0.0, price=price
    )


def plan(stations, miles):
    return plan_fuel_stops(stations, miles, tank_range_miles=RANGE, miles_per_gallon=MPG)


class PlanFuelStopsTests(SimpleTestCase):
    def test_short_trip_needs_one_stop(self):
        result = plan([station(1, 0, 3.00), station(2, 50, 3.50)], 300)
        self.assertEqual([(s.station_id, s.gallons) for s in result.stops], [(1, 30)])
        self.assertEqual(result.total_cost, 90.00)

    def test_buys_only_enough_to_reach_a_cheaper_station(self):
        result = plan([station(1, 0, 3.80), station(2, 280, 3.10)], 600)
        self.assertEqual([(s.station_id, s.gallons) for s in result.stops], [(1, 28), (2, 32)])
        self.assertEqual(result.total_cost, 205.60)

    def test_fills_up_when_nothing_cheaper_is_in_range(self):
        stations = [station(1, 0, 3.00), station(2, 300, 3.50), station(3, 450, 4.00)]
        result = plan(stations, 900)
        self.assertEqual(
            [(s.station_id, s.gallons) for s in result.stops], [(1, 50), (2, 30), (3, 10)]
        )
        self.assertEqual(result.total_cost, 295.00)

    def test_total_gallons_equal_distance_and_tank_is_never_overfilled(self):
        points = [
            (0, 3.6),
            (120, 3.2),
            (260, 3.9),
            (410, 3.0),
            (700, 3.4),
            (880, 3.8),
            (1050, 3.1),
            (1300, 3.5),
        ]
        stations = [station(i, mile, price) for i, (mile, price) in enumerate(points, start=1)]
        result = plan(stations, 1500)
        self.assertAlmostEqual(result.total_gallons, 150, places=3)
        self.assertAlmostEqual(sum(s.gallons for s in result.stops), 150, places=2)
        self.assertTrue(all(s.gallons <= RANGE / MPG + 1e-9 for s in result.stops))
        self.assertAlmostEqual(result.total_cost, sum(s.cost for s in result.stops), places=2)

    def test_cheaper_station_in_same_town_is_preferred(self):
        result = plan([station(1, 0, 3.50), station(2, 0, 3.00)], 100)
        self.assertEqual([s.station_id for s in result.stops], [2])

    def test_first_fill_up_covers_miles_from_origin(self):
        result = plan([station(1, 3, 3.00)], 100)
        self.assertEqual(result.stops[0].gallons, 10)
        self.assertEqual(result.stops[0].mile_marker, 3)

    def test_gap_longer_than_range_raises(self):
        with self.assertRaises(FuelGap):
            plan([station(1, 0, 3.00), station(2, 600, 3.00)], 700)

    def test_first_station_beyond_range_raises(self):
        with self.assertRaises(FuelGap):
            plan([station(1, 520, 3.00)], 900)

    def test_no_stations_raises(self):
        with self.assertRaises(FuelGap):
            plan([], 100)

    def test_zero_length_trip_costs_nothing(self):
        result = plan([], 0)
        self.assertEqual((result.stops, result.total_cost), ([], 0.0))
