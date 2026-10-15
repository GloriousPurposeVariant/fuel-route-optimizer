import logging

from rest_framework import status
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Return every API error as {"error": {"code": ..., "message": ...}}."""
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled error in %s", context["view"].__class__.__name__)
        return Response(
            {"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        code, message = _describe_validation_error(exc.detail)
    elif isinstance(exc, Throttled):
        code, message = "RATE_LIMITED", str(exc.detail)
    else:
        codes = exc.get_codes()
        code = codes.upper() if isinstance(codes, str) else "REQUEST_ERROR"
        message = str(exc.detail)

    response.data = {"error": {"code": code, "message": message}}
    return response


def _describe_validation_error(detail):
    if isinstance(detail, dict):
        for field, errors in detail.items():
            error = errors[0] if isinstance(errors, list) else errors
            if getattr(error, "code", None) in ("required", "blank", "null"):
                return "MISSING_PARAMETER", f"Query parameter '{field}' is required."
            return "INVALID_PARAMETER", f"{field}: {error}"
    first = detail[0] if isinstance(detail, list) and detail else detail
    return "INVALID_PARAMETER", str(first)
