from typing import Optional

from fastapi import APIRouter, Query

from app.models import ReleaseModel
from app.services.naive_keyword_search import get_relevant_notes

v1_router = APIRouter()


@v1_router.get("/get-relevant-notes")
async def get_relevant(
    major: int = Query(..., description="Major version number"),
    minor: int = Query(..., description="Minor version number"),
    keywords: Optional[list[str]] = Query(None, description="List of keywords to search for"),
):
    release = ReleaseModel(major=major, minor=minor)
    return get_relevant_notes(release, keywords)
