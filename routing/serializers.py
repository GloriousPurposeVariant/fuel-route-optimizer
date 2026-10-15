from django.conf import settings
from rest_framework import serializers


class RouteQuerySerializer(serializers.Serializer):
    start = serializers.CharField(max_length=120)
    finish = serializers.CharField(max_length=120)


class LocationSerializer(serializers.Serializer):
    query = serializers.CharField()
    name = serializers.CharField()
    lat = serializers.FloatField(source="latitude")
    lon = serializers.FloatField(source="longitude")


class FuelStopSerializer(serializers.Serializer):
    opis_id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    lat = serializers.FloatField(source="latitude")
    lon = serializers.FloatField(source="longitude")
    mile_marker = serializers.FloatField()
    distance_from_route_miles = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    gallons = serializers.FloatField()
    cost_usd = serializers.FloatField(source="cost")


class TripPlanSerializer(serializers.Serializer):
    start = LocationSerializer()
    finish = LocationSerializer()
    distance_miles = serializers.FloatField()
    duration_hours = serializers.FloatField()
    vehicle = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    fuel_stops = FuelStopSerializer(source="stops", many=True)
    route_geometry = serializers.SerializerMethodField()

    def get_vehicle(self, trip):
        return {
            "range_miles": settings.VEHICLE_RANGE_MILES,
            "miles_per_gallon": settings.VEHICLE_MPG,
        }

    def get_summary(self, trip):
        return {
            "total_gallons": trip.total_gallons,
            "total_fuel_cost_usd": trip.total_cost,
            "fuel_stop_count": len(trip.stops),
            "stations_considered": trip.stations_considered,
        }

    def get_route_geometry(self, trip):
        return {"type": "LineString", "coordinates": trip.geometry}
