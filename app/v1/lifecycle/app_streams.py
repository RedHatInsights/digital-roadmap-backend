import typing as t

from fastapi import APIRouter, Path
from fastapi.param_functions import Query

from app.data import MODULE_DATA

v1_router = APIRouter(
    prefix="/app-streams",
    tags=["lifecycle", "app streams"],
    responses={404: {"description": "Not found"}},
)


@v1_router.get("/")
async def get_app_streams(
    name: t.Annotated[str | None, Query(description="Module name")] = None,
):
    if name:
        result = []
        for modules in MODULE_DATA.values():
            for module in modules:
                if name.lower() in module["module_name"].lower():
                    result.append(module)

        return {"data": result}

    return {"data": [module for module in MODULE_DATA.values()]}


@v1_router.get("/{major_version}")
async def get_major_version(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
):
    return {"data": MODULE_DATA.get(major_version)}


@v1_router.get("/{major_version}/names")
async def get_module_names(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
) -> list[str]:
    data = MODULE_DATA.get(major_version, [])
    return [item["module_name"] for item in data]


@v1_router.get("/{major_version}/{module}")
async def get_module(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
    module: t.Annotated[str, Path(description="Module name")],
) -> str | list[dict[str, str]]:
    data = MODULE_DATA.get(major_version, [])
    if data:
        return sorted(item for item in data if item.get("module_name") == module)

    return "No matches"
