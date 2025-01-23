import typing as t

from fastapi import APIRouter, Path
from fastapi.param_functions import Query
from fastapi.responses import JSONResponse

from roadmap.data import MODULE_DATA

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
        for module in MODULE_DATA:
            if name.lower() in module["module_name"].lower():
                result.append(module)

        return {"data": result}

    return {"data": [module for module in MODULE_DATA]}


@v1_router.get("/{major_version}")
async def get_major_version(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
):
    return {"data": [module for module in MODULE_DATA if module.get("rhel_major_version", 0) == major_version]}


@v1_router.get("/{major_version}/names")
async def get_module_names(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
) -> dict[str, list[str]]:
    data = [module for module in MODULE_DATA if module.get("rhel_major_version", 0) == major_version]
    return {"names": sorted(item["module_name"] for item in data)}


@v1_router.get("/{major_version}/{module_name}")
async def get_module(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
    module_name: t.Annotated[str, Path(description="Module name")],
):
    if data := [module for module in MODULE_DATA if module.get("rhel_major_version", 0) == major_version]:
        if modules := sorted(item for item in data if item.get("module_name") == module_name):
            return {"data": modules}

    return JSONResponse(
        content={"message": "No modules matches query", "query": module_name},
        status_code=404,
    )
