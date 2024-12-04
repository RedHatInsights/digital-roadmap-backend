from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import get_paragraphs
from app.database import get_db
from app.models import TaggedParagraph

v1_router = APIRouter()


@v1_router.get("/get-relevant-notes")
async def get_relevant(
    major: int = Query(..., description="Major version number"),
    minor: int = Query(..., description="Minor version number"),
    keywords: Optional[list[str]] = Query(None, description="List of keywords to search for"),
    db: AsyncSession = Depends(get_db),
):

    # This is obviously not enough
    keyword = keywords[0] if keywords else "security"
    release_note_id = f"RHEL_{major}.{minor}"

    try:
        paragraphs = await get_paragraphs(db, release_note_id, keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        TaggedParagraph(
            title=paragraph["section_id"], text=paragraph["raw_text"], tag="h2", relevant=paragraph["relevant"]
        )
        for paragraph in paragraphs
    ]
