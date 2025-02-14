from fastapi import APIRouter

from . import app_streams
from . import rhel


router = APIRouter(prefix="/lifecycle", tags=["Lifecycle"])
router.include_router(app_streams.router)
router.include_router(rhel.router)
