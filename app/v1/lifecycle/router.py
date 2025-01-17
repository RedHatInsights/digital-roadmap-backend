from fastapi import APIRouter

from .app_streams import v1_router as app_streams_v1_router
from .systems import v1_router as systems_v1_router

v1_router = APIRouter()
v1_router.include_router(systems_v1_router)
v1_router.include_router(app_streams_v1_router)
