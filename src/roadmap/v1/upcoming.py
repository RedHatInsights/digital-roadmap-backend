import typing as t

from datetime import date
from functools import cache

from fastapi import APIRouter
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import TypeAdapter

from roadmap.common import ensure_date
from roadmap.config import Settings
from roadmap.models import Meta


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


class WrappedUpcomingResponse(BaseModel):
    meta: Meta
    data: list[UpcomingResponse]


@cache
def get_upcoming_data():
    with open(Settings.create().upcoming_json_path, "r") as file:
        upcomings = TypeAdapter(list[Upcoming]).validate_json(file.read())

    return [
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
async def get_upcoming() -> WrappedUpcomingResponse:
    data = get_upcoming_data()
    return {"meta": {"total": len(data), "count": len(data)}, "data": data}
