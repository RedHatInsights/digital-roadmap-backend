from fastapi import APIRouter

from . import lifecycle
from . import upcoming


router = APIRouter(prefix="/v1")
router.include_router(lifecycle.router)
router.include_router(lifecycle.app_streams.relevant)
router.include_router(lifecycle.rhel.relevant)
router.include_router(upcoming.router)
router.include_router(upcoming.relevant)
