from fastapi import APIRouter, Path

from app.data.systems import OS_DATA_MOCKED

v1_router = APIRouter()


@v1_router.get("/systems")
async def get_systems():
    systems = get_systems_data()

    return sorted(systems, key=lambda d: (d["major"], d["minor"]))


@v1_router.get("/systems/{major}")
async def get_systems_major(major: int = Path(..., description="Major version number")):
    systems = get_systems_data(major)

    return sorted(systems, key=lambda d: (d["major"], d["minor"]))


@v1_router.get("/systems/{major}/{minor}")
async def get_systems_major_minor(
    major: int = Path(..., description="Major version number"),
    minor: int = Path(..., description="Minor version number"),
):
    systems = get_systems_data(major, minor)

    return sorted(systems, key=lambda d: (d["major"], d["minor"]))


def get_systems_data(major=None, minor=None):
    data = OS_DATA_MOCKED

    if major is not None:
        data = [d for d in data if d["major"] == major]
    if minor is not None:
        data = [d for d in data if d["minor"] == minor]

    return data
