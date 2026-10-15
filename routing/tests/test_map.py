from django.test import SimpleTestCase
from django.urls import reverse


class MapPageTests(SimpleTestCase):
    def test_renders_form_prefilled_and_wired_to_api(self):
        response = self.client.get(reverse("map"), {"start": "Dallas, TX", "finish": "Chicago, IL"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Dallas, TX"')
        self.assertContains(response, "leaflet@1.9.4")
        self.assertContains(response, reverse("route"))
        self.assertContains(response, 'referrerPolicy: "strict-origin-when-cross-origin"')

    def test_user_input_is_escaped(self):
        response = self.client.get(reverse("map"), {"start": '"><script>alert(1)</script>'})
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_root_redirects_to_map_keeping_query(self):
        response = self.client.get("/", {"start": "Dallas, TX"})
        self.assertRedirects(
            response, f"{reverse('map')}?start=Dallas%2C+TX", fetch_redirect_response=False
        )
