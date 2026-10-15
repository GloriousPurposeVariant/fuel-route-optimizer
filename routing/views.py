from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import RouteQuerySerializer, TripPlanSerializer
from .services import plan_trip


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class RouteView(APIView):
    """GET /api/route/?start=City, ST&finish=City, ST"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "route"

    def get(self, request):
        query = RouteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        trip = plan_trip(query.validated_data["start"], query.validated_data["finish"])
        return Response(TripPlanSerializer(trip).data)
