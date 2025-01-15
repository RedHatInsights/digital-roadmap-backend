from fastapi import APIRouter

from app.data import UPCOMING_DATA

v1_router = APIRouter()


@v1_router.get("")
async def get_upcoming():
    # TODO: Replace fixture data with data from database
    return UPCOMING_DATA
