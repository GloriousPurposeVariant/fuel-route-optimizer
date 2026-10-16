from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from stations.models import City, FuelStation

PATCH_TARGET = "stations.management.commands.ensure_data.call_command"


class EnsureDataCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("ensure_data", *args, stdout=out)
        return out.getvalue()

    @mock.patch(PATCH_TARGET)
    def test_loads_everything_when_empty(self, loader):
        self.run_command()
        self.assertEqual(
            [c.args[0] for c in loader.call_args_list], ["load_cities", "load_stations"]
        )

    @mock.patch(PATCH_TARGET)
    def test_skips_when_data_exists(self, loader):
        City.objects.create(name="Alpha", state="TX", key="alpha", latitude=35.0, longitude=-100.0)
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
        output = self.run_command()
        loader.assert_not_called()
        self.assertIn("skipping", output)

    @mock.patch(PATCH_TARGET)
    def test_force_reloads(self, loader):
        City.objects.create(name="Alpha", state="TX", key="alpha", latitude=35.0, longitude=-100.0)
        self.run_command("--force")
        self.assertEqual(loader.call_count, 2)
