import typing as t

from operator import attrgetter

from fastapi import APIRouter
from fastapi import Path
from fastapi import Request

from roadmap.common import get_system_count_from_inventory
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import System


router = APIRouter(
    prefix="/rhel",
    tags=["RHEL"],
)


@router.get("/")
async def get_systems(request: Request) -> list[System]:
    systems_response = await get_system_count_from_inventory(request.headers)
    systems = get_systems_data()

    for system in systems:
        system.count = 0
        for item in systems_response.get("results", []):
            value = item["value"]
            if (system.name, system.major, system.minor) == (value["name"], value["major"], value["minor"]):
                system.count = item["count"]
                break

    return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


@router.get("/{major}")
async def get_systems_major(major: t.Annotated[int, Path(description="Major version number")]) -> list[System]:
    systems = get_systems_data(major)

    return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


@router.get("/{major}/{minor}")
async def get_systems_major_minor(
    major: int = Path(..., description="Major version number"),
    minor: int = Path(..., description="Minor version number"),
):
    systems = get_systems_data(major, minor)

    return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


def get_systems_data(major=None, minor=None):
    data = [
        System(
            name=item.name,
            major=item.major,
            minor=getattr(item, "minor", None) or 0,
            release="release",
            release_date=item.start,
            retirement_date=item.end,
            lifecycle_type="lifecycle type",
        )
        for item in OS_LIFECYCLE_DATES.values()
        if getattr(item, "minor") is not None
    ]

    if major is not None:
        data = [item for item in data if item.major == major]
    if minor is not None:
        data = [item for item in data if item.minor == minor]

    return data
