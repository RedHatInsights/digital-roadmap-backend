from fastapi import APIRouter

from . import lifecycle, release_notes, upcoming

router = APIRouter(prefix="/v1")
router.include_router(lifecycle.router)
router.include_router(release_notes.router)
router.include_router(upcoming.router)
