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
from pydantic import computed_field
from pydantic import Field
from pydantic import TypeAdapter

from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import query_host_inventory
from roadmap.common import rhel_major_minor
from roadmap.config import Settings
from roadmap.models import _get_system_uuids
from roadmap.models import Meta
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import NEVRA


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


def _get_first_sorted_package(packages: set[str]) -> str:
    """Returns the first package from sorted packages set"""
    return sorted(packages)[0] if packages else ""


class UpcomingInput(BaseModel):
    name: str
    type: UpcomingType
    packages: set[str]
    release: str
    os_major: int = Field(default_factory=lambda data: int(data["release"].partition(".")[0]))
    date: Date
    details: UpcomingInputDetails

    @computed_field
    @property
    def package(self) -> str:
        """Returns the first package from sorted packages set for backward compatibility."""
        return _get_first_sorted_package(self.packages)


class UpcomingOutputDetails(BaseModel):
    architecture: Architecture | None
    detailFormat: int
    summary: str
    trainingTicket: str
    dateAdded: date = Field(default_factory=date.today)
    lastModified: Date
    potentiallyAffectedSystemsCount: int
    potentiallyAffectedSystemsDetail: set[SystemInfo]
    potentiallyAffectedSystems: set[UUID] = Field(default_factory=_get_system_uuids)


class UpcomingOutput(BaseModel):
    name: str
    type: UpcomingType
    packages: set[str]
    release: str
    date: Date
    details: UpcomingOutputDetails

    @computed_field
    @property
    def package(self) -> str:
        """Returns the first package from packages set for backward compatibility."""
        return _get_first_sorted_package(self.packages)


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


async def packages_by_system(
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[t.Any, Depends(query_host_inventory)],
) -> dict[SystemInfo, set[str]]:
    logger.info(f"Getting packages by system for {org_id or 'UNKNOWN'}")

    missing = defaultdict(int)
    packages_by_system = defaultdict(set)
    async for system in systems.yield_per(2_000).mappings():
        packages = system["packages"] or []

        try:
            os_major, os_minor = rhel_major_minor(system)
        except ValueError:
            missing["os_version"] += 1
            continue

        if not packages:
            missing["packages"] += 1
            continue

        system_info = SystemInfo(
            id=system["id"], display_name=system["display_name"], os_major=os_major, os_minor=os_minor
        )

        # The time and space complexity of this line is very high.
        # The result of NEVRA.from_string() is cached, which helps a lot.
        #
        # In the future, it will most likely be necessary to store the NEVRA object and not just
        # the package name to improve matching.
        packages_by_system[system_info] = {NEVRA.from_string(package).name for package in packages}

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    return packages_by_system


def get_upcoming_data_with_hosts(
    packages_by_system: t.Annotated[t.Any, Depends(packages_by_system)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    all: bool = False,
) -> list[UpcomingOutput]:
    os_major_versions = {system.os_major for system in packages_by_system}
    try:
        os_major_versions.remove(None)
    except KeyError:
        pass

    result = []
    for upcoming in read_upcoming_file(settings.upcoming_json_path):
        systems = set()
        for system, packages in packages_by_system.items():
            if upcoming.packages.intersection(packages):
                systems.add(system)

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
            potentiallyAffectedSystemsDetail=systems,
        )

        result.append(
            UpcomingOutput(
                name=upcoming.name,
                type=upcoming.type,
                packages=upcoming.packages,
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
        data = [d for d in data if d.details.potentiallyAffectedSystemsDetail]

    return {
        "meta": {
            "total": len(data),
            "count": len(data),
        },
        "data": data,
    }
