from fastapi import APIRouter

from app.v1.lifecycle.systems.endpoints import v1_router as systems_v1_router

v1_router = APIRouter()

v1_router.include_router(systems_v1_router, tags=["lifecycle-systems"])
