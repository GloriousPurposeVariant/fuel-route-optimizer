import logging
import time

from django.db import DatabaseError

from .corridor import get_station_index

logger = logging.getLogger(__name__)


def warm_up():
    """Build in-memory indexes before the first request, so no user pays that cost."""
    started = time.perf_counter()
    try:
        index = get_station_index()
    except DatabaseError:
        logger.warning(
            "Warm-up skipped: database not ready. Run migrate, load_cities and load_stations."
        )
        return
    if not len(index.ids):
        logger.warning("Warm-up: no fuel stations loaded. Run load_cities and load_stations.")
        return
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("Warm-up: %d stations indexed in %.0f ms", len(index.ids), elapsed_ms)
