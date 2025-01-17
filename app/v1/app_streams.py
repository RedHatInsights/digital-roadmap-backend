from fastapi import APIRouter

from app.data import MODULE_DATA

v1_router = APIRouter()

@v1_router.get("")
async def get_app_streams():
    return ["all the things"]

@v1_router.get("/{major_version}")
async def get_major_version(major_version: int):
    return MODULE_DATA.get(major_version)


@v1_router.get("/{major_version}/names")
async def get_module_names(major_version: int):
    data = MODULE_DATA.get(major_version, [])
    return [item["module_name"] for item in data]


@v1_router.get("/{major_version}/{module}")
async def get_module(
    major_version: int,
    module: str,
    ):
    data = MODULE_DATA.get(major_version, [])
    if data:
        return sorted(item for item in data if item.get("module_name") == module)

    return "No matches"
