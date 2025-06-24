import logging
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


logger = logging.getLogger("uvicorn.error")

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
    os_major: int = Field(default_factory=lambda data: int(data["release"].partition(".")[0]))
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
    potentiallyAffectedSystems: set[UUID]


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
    response_model=WrappedUpcomingInput,
)
async def get_upcoming(data: t.Annotated[t.Any, Depends(get_upcoming_data_no_hosts)]):
    return {
        "meta": {
            "total": len(data),
            "count": len(data),
        },
        "data": data,
    }


def get_upcoming_data_with_hosts(
    systems_by_app_stream: t.Annotated[dict[AppStreamKey, set[UUID]], Depends(systems_by_app_stream)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    all: bool = False,
) -> list[UpcomingOutput]:
    keys_by_name = defaultdict(list)
    os_major_versions = set()
    for system in systems_by_app_stream:
        keys_by_name[system.name].append(system)
        os_major_versions.add(system.app_stream_entity.os_major)

    try:
        os_major_versions.remove(None)
    except KeyError:
        pass

    result = []
    for upcoming in read_upcoming_file(settings.upcoming_json_path):
        systems = set()
        for key in keys_by_name[upcoming.package]:
            systems.update(systems_by_app_stream[key])

        if not all:
            # If the roadmap item doesn't match the major OS version of a host
            # in inventory, do not include it.
            if upcoming.os_major not in os_major_versions:
                continue

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


@relevant.get(
    "",
    summary="Upcoming changes, deprecations, additions, and enhancements relevant to requester's systems",
    response_model=WrappedUpcomingOutput,
)
async def get_upcoming_relevant(
    data: t.Annotated[t.Any, Depends(get_upcoming_data_with_hosts)],
    all: bool = False,
):
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
