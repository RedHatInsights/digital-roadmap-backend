from fastapi import APIRouter

from roadmap.v1 import lifecycle
from roadmap.v1 import upcoming

from . import relevant_app_streams
from . import relevant_rhel
from . import relevant_upcoming


router = APIRouter(prefix="/v2")

# Re-export v1 static catalog routers under v2 prefix (unchanged behavior)
router.include_router(lifecycle.router)
router.include_router(upcoming.router)

# v2 relevant endpoints (wrapper + systems)
router.include_router(relevant_rhel.relevant)
router.include_router(relevant_app_streams.relevant)
router.include_router(relevant_upcoming.relevant)
