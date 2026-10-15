from django.test import SimpleTestCase

from routing.corridor import StationIndex, find_corridor_stations, resample_route
from routing.geo import segment_lengths_miles
from routing.ors import Route

# A straight east-west route along latitude 35: about 56.7 miles.
COORDINATES = [[-100.0, 35.0], [-99.0, 35.0]]
ROUTE_MILES = float(segment_lengths_miles([-100.0, -99.0], [35.0, 35.0])[0])
ROUTE = Route(coordinates=COORDINATES, distance_miles=ROUTE_MILES, duration_hours=1.0)


class ResampleRouteTests(SimpleTestCase):
    def test_one_point_per_mile_ending_at_destination(self):
        lon, lat, markers = resample_route(COORDINATES, ROUTE_MILES)
        self.assertEqual(markers[0], 0)
        self.assertAlmostEqual(markers[-1], ROUTE_MILES)
        self.assertLessEqual(max(markers[1:] - markers[:-1]), 1.0 + 1e-9)
        self.assertAlmostEqual(lon[-1], -99.0)

    def test_scales_to_reported_road_distance(self):
        _, _, markers = resample_route(COORDINATES, 60.0)
        self.assertAlmostEqual(markers[-1], 60.0)

    def test_repeated_points_are_ignored(self):
        _, _, markers = resample_route([[-100.0, 35.0], [-100.0, 35.0], [-99.0, 35.0]], ROUTE_MILES)
        self.assertAlmostEqual(markers[-1], ROUTE_MILES)


class FindCorridorStationsTests(SimpleTestCase):
    def setUp(self):
        self.index = StationIndex.from_rows(
            [
                (1, 3.10, 35.0, -99.5),  # on the route, halfway
                (2, 2.90, 35.1, -99.9),  # about 7 miles north, near the start
                (3, 2.50, 35.3, -99.5),  # about 21 miles north: outside a 10-mile corridor
            ]
        )

    def test_keeps_only_stations_within_radius_sorted_by_mile(self):
        result = find_corridor_stations(ROUTE, radius_miles=10, index=self.index)
        self.assertEqual([s.station_id for s in result], [2, 1])
        self.assertAlmostEqual(result[1].mile_marker, ROUTE_MILES / 2, delta=1)
        self.assertAlmostEqual(result[0].distance_from_route_miles, 6.9, delta=0.3)

    def test_wider_radius_includes_farther_station(self):
        result = find_corridor_stations(ROUTE, radius_miles=25, index=self.index)
        self.assertEqual(len(result), 3)

    def test_empty_index_returns_nothing(self):
        self.assertEqual(find_corridor_stations(ROUTE, index=StationIndex.from_rows([])), [])
