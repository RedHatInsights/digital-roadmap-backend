import typing as t

from collections import defaultdict
from datetime import date
from enum import auto
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import Field
from pydantic import TypeAdapter

from roadmap.common import ensure_date
from roadmap.config import Settings
from roadmap.models import Meta
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream


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


class UpcomingInputDetails(BaseModel):
    architecture: Architecture | None
    detailFormat: int
    summary: str
    trainingTicket: str
    dateAdded: date = Field(default_factory=date.today)
    lastModified: Date


class UpcomingInput(BaseModel):
    name: str
    type: UpcomingType
    package: str
    release: str
    date: Date
    details: UpcomingInputDetails


class UpcomingOutputDetails(BaseModel):
    architecture: Architecture | None
    detailFormat: int
    summary: str
    trainingTicket: str
    dateAdded: date = Field(default_factory=date.today)
    lastModified: Date
    potentiallyAffectedSystemsCount: int
    potentiallyAffectedSystems: list[UUID]


class UpcomingOutput(BaseModel):
    name: str
    type: UpcomingType
    package: str
    release: str
    date: Date
    details: UpcomingOutputDetails


class WrappedUpcomingOutput(BaseModel):
    meta: Meta
    data: list[UpcomingOutput]


class WrappedUpcomingInput(BaseModel):
    meta: Meta
    data: list[UpcomingInput]


@lru_cache
def read_upcoming_file(file: Path) -> list[UpcomingInput]:
    return TypeAdapter(list[UpcomingInput]).validate_json(file.read_text())


def get_upcoming_data_no_hosts(settings: t.Annotated[Settings, Depends(Settings.create)]) -> list[UpcomingInput]:
    return read_upcoming_file(settings.upcoming_json_path)


@router.get(
    "",
    summary="Upcoming changes, deprecations, additions, and enhancements",
)
async def get_upcoming(data: t.Annotated[t.Any, Depends(get_upcoming_data_no_hosts)]) -> WrappedUpcomingInput:
    return {
        "meta": {
            "total": len(data),
            "count": len(data),
        },
        "data": data,
    }


def get_upcoming_data_with_hosts(
    systems_by_stream: t.Annotated[dict[AppStreamKey, list[UUID]], Depends(systems_by_app_stream)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
) -> list[UpcomingOutput]:
    keys_by_name = defaultdict(list)
    [keys_by_name[a.name].append(a) for a in systems_by_stream.keys()]

    result = []
    for upcoming in read_upcoming_file(settings.upcoming_json_path):
        systems = set()
        for key in keys_by_name[upcoming.package]:
            systems.update(systems_by_stream[key])

        details = UpcomingOutputDetails(
            architecture=upcoming.details.architecture,
            detailFormat=upcoming.details.detailFormat,
            summary=upcoming.details.summary,
            trainingTicket=upcoming.details.trainingTicket,
            dateAdded=upcoming.details.dateAdded,
            lastModified=upcoming.details.lastModified,
            potentiallyAffectedSystemsCount=len(systems),
            potentiallyAffectedSystems=systems,
        )

        result.append(
            UpcomingOutput(
                name=upcoming.name,
                type=upcoming.type,
                package=upcoming.package,
                release=upcoming.release,
                date=upcoming.date,
                details=details,
            )
        )
    return result


relevant = APIRouter(
    prefix="/relevant/upcoming-changes",
    tags=["Relevant", "Upcoming Changes"],
)


@relevant.get("", summary="Upcoming changes, deprecations, additions, and enhancements relevant to requester's systems")
async def get_upcoming_relevant(
    data: t.Annotated[t.Any, Depends(get_upcoming_data_with_hosts)], all: bool = False
) -> WrappedUpcomingOutput:
    """
    Returns a list of upcoming changes to packages.

    Data includes requester's potentially affected systems.

    If 'all' is True, all known changes are returned, not just those
    potentially affecting the requester's systems.

    """
    if not all:
        data = [d for d in data if d.details.potentiallyAffectedSystems]
    return {
        "meta": {
            "total": len(data),
            "count": len(data),
        },
        "data": data,
    }
