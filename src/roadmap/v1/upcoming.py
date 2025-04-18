import os
import typing as t

from datetime import date
from pathlib import Path

from fastapi import APIRouter
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import TypeAdapter

from roadmap.common import ensure_date


router = APIRouter(prefix="/upcoming-changes", tags=["Upcoming Changes"])

Date = t.Annotated[str | date | None, AfterValidator(ensure_date)]


class Upcoming(BaseModel):
    ticket: str
    title: str
    summary: str
    type: str
    package: str
    architecture: str
    release: str
    release_date: Date


if not (filename := os.environ.get("ROADMAP_UPCOMING_JSON_PATH")):
    filename = Path(__file__).parent.parent.joinpath("data").resolve().joinpath("upcoming.json")

with open(filename, "r") as file:
    upcomings = TypeAdapter(list[Upcoming]).validate_json(file.read())


class UpcomingResponseDetails(BaseModel):
    detailFormat: int
    summary: str
    potentiallyAffectedSystems: int
    trainingTicket: str
    dateAdded: Date
    lastModified: Date


class UpcomingResponse(BaseModel):
    name: str
    type: str
    release: str
    date: Date
    details: UpcomingResponseDetails


UPCOMING_DATA = [
    UpcomingResponse(
        name=upcoming.title,
        type=upcoming.type,
        release=upcoming.release,
        date=upcoming.release_date,
        details=UpcomingResponseDetails(
            detailFormat=0,
            summary=upcoming.summary,
            potentiallyAffectedSystems=5,
            trainingTicket=upcoming.ticket,
            dateAdded=date(2024, 10, 29),
            lastModified=date(2024, 10, 29),
        ),
    )
    for upcoming in upcomings
]


@router.get("")
async def get_upcoming() -> list[UpcomingResponse]:
    return UPCOMING_DATA
