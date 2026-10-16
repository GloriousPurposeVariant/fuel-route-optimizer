from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import RouteQuerySerializer, TripPlanSerializer
from .services import plan_trip


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


def route_map(request):
    """HTML page that calls /api/route/ from the browser and draws the result with Leaflet."""
    context = {"start": request.GET.get("start", ""), "finish": request.GET.get("finish", "")}
    return render(request, "routing/map.html", context)


class RouteView(APIView):
    """GET /api/route/?start=City, ST&finish=City, ST"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "route"

    def get(self, request):
        query = RouteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        trip = plan_trip(query.validated_data["start"], query.validated_data["finish"])
        response = Response(TripPlanSerializer(trip, context={"request": request}).data)
        response["X-Route-Cache"] = "HIT" if trip.route_cache_hit else "MISS"
        response["Server-Timing"] = ", ".join(
            f"{name};dur={duration}" for name, duration in trip.timings_ms.items()
        )
        return response
