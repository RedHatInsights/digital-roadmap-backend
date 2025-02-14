from fastapi import APIRouter

from roadmap.data import UPCOMING_DATA


router = APIRouter(prefix="/upcoming-changes", tags=["Upcoming Changes"])


@router.get("/")
async def get_upcoming():
    # TODO: Replace fixture data with data from database
    return UPCOMING_DATA
