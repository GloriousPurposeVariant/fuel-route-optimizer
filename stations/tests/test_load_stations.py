import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from stations.models import City, FuelStation

CSV = """OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
1,STOP A,"I-35, EXIT 1",Alpha      ,TX,100,3.50
1,STOP A DBA CHEAPER,"I-35, EXIT 1",Alpha,TX,100,3.20
2,CANADA STOP,HWY 1,Toronto,ON,200,4.00
3,NOWHERE STOP,I-10,Atlantis,TX,100,3.00
4,SAINT STOP,I-70,Saint Peters,MO,300,3.10
"""


class LoadStationsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        City.objects.create(name="Alpha", state="TX", key="alpha", latitude=35.0, longitude=-100.0)
        City.objects.create(
            name="St. Peters", state="MO", key="stpeters", latitude=38.8, longitude=-90.6
        )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.tmp.name) / "prices.csv"
        self.csv_path.write_text(CSV, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        out = StringIO()
        call_command("load_stations", csv=str(self.csv_path), stdout=out)
        return out.getvalue()

    def test_cleans_dedupes_and_geocodes(self):
        output = self.load()

        self.assertEqual(FuelStation.objects.count(), 2)
        alpha = FuelStation.objects.get(opis_id=1)
        self.assertEqual(alpha.price, Decimal("3.20"))
        self.assertEqual(alpha.name, "STOP A DBA CHEAPER")
        self.assertEqual(alpha.city, "Alpha")
        self.assertEqual(FuelStation.objects.get(opis_id=4).latitude, 38.8)

        self.assertRegex(output, r"Rows read:\s+5")
        self.assertRegex(output, r"Dropped non-US rows:\s+1")
        self.assertRegex(output, r"Dropped duplicate rows:\s+1")
        self.assertRegex(output, r"Skipped, city not found:\s+1")
        self.assertIn("Atlantis, TX", output)

    def test_is_idempotent(self):
        self.load()
        self.load()
        self.assertEqual(FuelStation.objects.count(), 2)

    def test_requires_cities(self):
        City.objects.all().delete()
        with self.assertRaises(CommandError):
            self.load()

    def test_missing_csv(self):
        with self.assertRaises(CommandError):
            call_command("load_stations", csv="does/not/exist.csv", stdout=StringIO())
