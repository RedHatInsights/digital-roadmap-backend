import typing as t

from datetime import date
from enum import auto
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import Field
from pydantic import TypeAdapter

from roadmap.common import ensure_date
from roadmap.config import Settings
from roadmap.models import Meta


router = APIRouter(prefix="/upcoming-changes", tags=["Upcoming Changes"])

Date = t.Annotated[str | date | None, AfterValidator(ensure_date)]


class UpcomingType(StrEnum):
    addition = auto()
    change = auto()
    deprecation = auto()
    enhancement = auto()


class Architecture(StrEnum):
    arch64 = auto()
    x86_64 = auto()
    s390x = auto()
    ppc64le = auto()
    none = ""


class UpcomingDetails(BaseModel):
    architecture: Architecture | None
    detailFormat: int
    summary: str
    potentiallyAffectedSystems: int
    trainingTicket: str
    dateAdded: date = Field(default_factory=date.today)
    lastModified: Date


class Upcoming(BaseModel):
    name: str
    type: UpcomingType
    release: str
    date: Date
    details: UpcomingDetails


class WrappedUpcoming(BaseModel):
    meta: Meta
    data: list[Upcoming]


@lru_cache
def read_upcoming_file(file: str | Path) -> list[Upcoming]:
    with open(file, "r") as file:
        return TypeAdapter(list[Upcoming]).validate_json(file.read())


def get_upcoming_data(settings: t.Annotated[Settings, Depends(Settings.create)]) -> list[Upcoming]:
    return read_upcoming_file(settings.upcoming_json_path)


@router.get(
    "",
    summary="Upcoming changes, deprecations, additions, and enhancements",
)
async def get_upcoming(data: t.Annotated[t.Any, Depends(get_upcoming_data)]) -> WrappedUpcoming:
    return {
        "meta": {
            "total": len(data),
            "count": len(data),
        },
        "data": data,
    }
