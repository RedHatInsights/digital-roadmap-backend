from fastapi import APIRouter

from . import lifecycle
from . import relevant_upcoming_hosts
from . import upcoming
from .lifecycle import host_uuids
from .lifecycle import relevant_app_streams_hosts
from .lifecycle import relevant_rhel_hosts


router = APIRouter(prefix="/v1")
router.include_router(lifecycle.router)
router.include_router(lifecycle.app_streams.relevant)
router.include_router(lifecycle.rhel.relevant)
router.include_router(relevant_app_streams_hosts.router)
router.include_router(relevant_rhel_hosts.router)
router.include_router(host_uuids.router)
router.include_router(upcoming.router)
router.include_router(upcoming.relevant)
router.include_router(relevant_upcoming_hosts.router)
