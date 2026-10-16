from django.test import SimpleTestCase

from stations.normalize import census_aliases, city_key, strip_census_suffix


class CityKeyTests(SimpleTestCase):
    def test_equivalent_spellings_share_a_key(self):
        pairs = [
            ("Saint Peters", "St. Peters"),
            ("Mount Jackson", "Mt Jackson"),
            ("Fort Worth", "Ft. Worth"),
            ("Mc Graw", "McGraw"),
            ("S Coffeyville", "South Coffeyville"),
            ("Monroe Township", "Monroe"),
            ("Winston Salem", "Winston-Salem"),
            ("  Prairie Du Chien ", "Prairie du Chien"),
        ]
        for csv_name, census_name in pairs:
            with self.subTest(csv_name=csv_name):
                self.assertEqual(city_key(csv_name), city_key(census_name))

    def test_different_places_keep_different_keys(self):
        self.assertNotEqual(city_key("Salem"), city_key("Winston-Salem"))


class CensusNameTests(SimpleTestCase):
    def test_strip_census_suffix(self):
        self.assertEqual(strip_census_suffix("Dallas city"), "Dallas")
        self.assertEqual(strip_census_suffix("Edison township"), "Edison")
        self.assertEqual(strip_census_suffix("Hogansburg CDP"), "Hogansburg")
        self.assertEqual(strip_census_suffix("Prairie du Chien city"), "Prairie du Chien")

    def test_aliases(self):
        self.assertEqual(census_aliases("Boise City"), {"Boise"})
        self.assertEqual(census_aliases("Nashville-Davidson"), {"Nashville", "Davidson"})
        self.assertEqual(census_aliases("Dallas"), set())
