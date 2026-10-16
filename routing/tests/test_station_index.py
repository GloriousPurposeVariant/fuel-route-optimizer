from django.test import TestCase

from routing.corridor import clear_station_index, get_station_index
from stations.models import FuelStation


class StationIndexTests(TestCase):
    def setUp(self):
        clear_station_index()

    def tearDown(self):
        clear_station_index()

    def test_empty_index_is_not_cached(self):
        self.assertEqual(len(get_station_index().ids), 0)
        FuelStation.objects.create(
            opis_id=1,
            name="Stop",
            address="I-40",
            city="Alpha",
            state="TX",
            rack_id=1,
            price="3.00",
            latitude=35.0,
            longitude=-100.0,
        )
        self.assertEqual(len(get_station_index().ids), 1)

    def test_index_is_built_once(self):
        FuelStation.objects.create(
            opis_id=1,
            name="Stop",
            address="I-40",
            city="Alpha",
            state="TX",
            rack_id=1,
            price="3.00",
            latitude=35.0,
            longitude=-100.0,
        )
        first = get_station_index()
        with self.assertNumQueries(0):
            self.assertIs(get_station_index(), first)
