import logging
import time

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    """Log every request's duration and return it in an X-Response-Time-ms header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.get_full_path(),
            response.status_code,
            elapsed_ms,
        )
        return response
