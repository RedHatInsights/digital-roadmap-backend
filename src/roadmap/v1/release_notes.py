from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.crud import get_paragraphs
from roadmap.database import get_db
from roadmap.models import TaggedParagraph


router = APIRouter(prefix="/release-notes", tags=["Release Notes"])


@router.get("")
async def get_release_notes(
    major: int = Query(..., description="Major version number"),
    minor: int = Query(..., description="Minor version number"),
    keywords: Optional[list[str]] = Query(None, description="List of keywords to search for"),
    db: AsyncSession = Depends(get_db),
):
    release_note_id = f"RHEL_{major}.{minor}"
    keyword = keywords or ["security"]

    try:
        paragraphs = await get_paragraphs(db, release_note_id, keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        TaggedParagraph(
            title=paragraph["section_id"],
            text=paragraph["raw_text"],
            tag="h2",
        )
        for paragraph in paragraphs
    ]
