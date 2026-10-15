from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings

from routing.exceptions import NoRouteFound, RouteTooLong, RoutingUnavailable
from routing.locations import Location
from routing.ors import get_route

START = Location("Dallas, TX", "Dallas, TX", 32.79, -96.77)
FINISH = Location("Chicago, IL", "Chicago, IL", 41.84, -87.68)


def fake_response(status_code, payload):
    response = mock.Mock(status_code=status_code)
    response.json.return_value = payload
    return response


@override_settings(ORS_API_KEY="test-key")
class GetRouteTests(SimpleTestCase):
    @mock.patch("routing.ors.requests.post")
    def test_parses_route_with_one_call(self, post):
        post.return_value = fake_response(
            200,
            {
                "features": [
                    {
                        "geometry": {"coordinates": [[-96.77, 32.79], [-87.68, 41.84]]},
                        "properties": {"summary": {"distance": 925.4, "duration": 50400}},
                    }
                ]
            },
        )
        route = get_route(START, FINISH)
        self.assertEqual(route.distance_miles, 925.4)
        self.assertEqual(route.duration_hours, 14)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["coordinates"][0], [-96.77, 32.79])

    @mock.patch("routing.ors.requests.post")
    def test_unroutable_point_is_no_route(self, post):
        post.return_value = fake_response(
            404, {"error": {"code": 2010, "message": "Could not find routable point"}}
        )
        with self.assertRaises(NoRouteFound):
            get_route(START, FINISH)

    @mock.patch("routing.ors.requests.post")
    def test_quota_exceeded_is_unavailable(self, post):
        post.return_value = fake_response(429, {"error": "Rate limit exceeded"})
        with self.assertRaises(RoutingUnavailable):
            get_route(START, FINISH)

    @mock.patch("routing.ors.requests.post", side_effect=requests.Timeout)
    def test_timeout_is_unavailable(self, post):
        with self.assertRaises(RoutingUnavailable):
            get_route(START, FINISH)

    @override_settings(ORS_API_KEY="")
    def test_missing_key_is_unavailable(self):
        with self.assertRaises(RoutingUnavailable):
            get_route(START, FINISH)

    @mock.patch("routing.ors.requests.post")
    def test_request_never_crosses_borders(self, post):
        post.return_value = fake_response(
            200,
            {
                "features": [
                    {
                        "geometry": {"coordinates": [[-96.77, 32.79], [-87.68, 41.84]]},
                        "properties": {"summary": {"distance": 925.4, "duration": 50400}},
                    }
                ]
            },
        )
        get_route(START, FINISH)
        self.assertEqual(post.call_args.kwargs["json"]["options"], {"avoid_borders": "all"})

    @mock.patch("routing.ors.requests.post")
    def test_server_limit_is_route_too_long(self, post):
        post.return_value = fake_response(
            400,
            {
                "error": {
                    "code": 2004,
                    "message": "Request parameters exceed the server configuration limits.",
                }
            },
        )
        with self.assertRaises(RouteTooLong):
            get_route(START, FINISH)
