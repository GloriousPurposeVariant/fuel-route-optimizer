from rest_framework import status
from rest_framework.exceptions import APIException


class RoutingError(APIException):
    """Base class. Each subclass has its own HTTP status and machine-readable code."""


class InvalidLocation(RoutingError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Location must be in 'City, ST' format."
    default_code = "INVALID_LOCATION_FORMAT"


class LocationNotInUSA(RoutingError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Location must be within the USA."
    default_code = "LOCATION_NOT_IN_USA"


class LocationNotFound(RoutingError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Location could not be found."
    default_code = "LOCATION_NOT_FOUND"


class NoRouteFound(RoutingError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "No drivable route between these locations."
    default_code = "NO_ROUTE"


class RoutingUnavailable(RoutingError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The routing service is unavailable. Try again later."
    default_code = "ROUTING_UNAVAILABLE"


class UnsupportedRegion(RoutingError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Routing is only supported within the contiguous United States."
    default_code = "UNSUPPORTED_REGION"


class RouteTooLong(RoutingError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Route is longer than the routing service allows."
    default_code = "ROUTE_TOO_LONG"


class FuelGap(RoutingError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Part of the route has no fuel station within the vehicle's range."
    default_code = "FUEL_GAP"
