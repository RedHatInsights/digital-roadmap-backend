"""Cache management for the notificator.

The NEVRA parser and app-stream package lookup use ``@functools.cache``
(unbounded) to speed up repeated lookups within a single org.  When the
notificator processes many orgs sequentially, those caches grow
monotonically and can consume hundreds of megabytes of memory.

Calling ``clear_caches()`` between orgs bounds memory to the size of the
single largest org while keeping the within-org caching benefit intact.
"""

import structlog

from roadmap.v1.lifecycle.app_streams import app_stream_from_package
from roadmap.v1.lifecycle.app_streams import NEVRA


logger = structlog.get_logger(__name__)


def clear_caches() -> None:
    """Clear NEVRA and app-stream package caches to reclaim memory."""
    nevra_info = NEVRA.from_string.cache_info()
    app_stream_info = app_stream_from_package.cache_info()

    NEVRA.from_string.cache_clear()
    app_stream_from_package.cache_clear()

    logger.debug(
        "Cleared inter-org caches",
        nevra_cache_size=nevra_info.currsize,
        app_stream_cache_size=app_stream_info.currsize,
    )
