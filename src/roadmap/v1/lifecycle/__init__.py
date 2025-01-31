from fastapi import APIRouter

from . import app_streams, systems

router = APIRouter(prefix="/lifecycle")
router.include_router(app_streams.router)
router.include_router(systems.router)
