import typing as t

from operator import attrgetter

from fastapi import APIRouter
from fastapi import Header
from fastapi import Response
from fastapi import Path
from fastapi import Request

from roadmap.common import get_all_systems
from roadmap.data.systems import OS_DATA_MOCKED
from roadmap.models import System


router = APIRouter(
    prefix="/rhel",
    tags=["RHEL"],
)


@router.get("/")
async def get_systems(request: Request):
    inventory_systems = await get_all_systems(request.headers)
    return Response(inventory_systems)

    systems = get_systems_data()

    return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


@router.get("/{major}")
    systems = get_systems_data(major)
async def get_systems_major(major: t.Annotated[int, Path(description="Major version number")]) -> list[System]:

    return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


@router.get("/{major}/{minor}")
async def get_systems_major_minor(
    major: int = Path(..., description="Major version number"),
    minor: int = Path(..., description="Minor version number"),
):
    systems = get_systems_data(major, minor)

    return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


def get_systems_data(major=None, minor=None):
    data = OS_DATA_MOCKED

    if major is not None:
        data = [d for d in data if d.major == major]
    if minor is not None:
        data = [d for d in data if d.minor == minor]

    return data
