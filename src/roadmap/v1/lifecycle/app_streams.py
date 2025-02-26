import typing as t

from fastapi import APIRouter
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from fastapi.params import Depends
from pydantic import BaseModel

from roadmap.data import MODULE_DATA
from roadmap.models import Meta


class AppStreamsResponse(BaseModel):
    meta: Meta
    data: list[dict]


class AppStreamsNamesResponse(BaseModel):
    meta: Meta
    data: list[str]


router = APIRouter(
    prefix="/app-streams",
    tags=["App Streams"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=AppStreamsResponse)
async def get_app_streams(
    name: t.Annotated[str | None, Query(description="Module name")] = None,
):
    if name:
        result = [module for module in MODULE_DATA if name.lower() in module["module_name"].lower()]

        return {
            "meta": {"total": len(result), "count": len(result)},
            "data": result,
        }

    return {
        "meta": {"total": len(MODULE_DATA), "count": len(MODULE_DATA)},
        "data": [module for module in MODULE_DATA],
    }


@router.get("/{major_version}", response_model=AppStreamsResponse)
async def get_major_version(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
):
    modules = [module for module in MODULE_DATA if module.get("rhel_major_version", 0) == major_version]
    return {
        "meta": {"total": len(modules), "count": len(modules)},
        "data": modules,
    }


@router.get("/{major_version}/names", response_model=AppStreamsNamesResponse)
async def get_module_names(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
):
    modules = [module for module in MODULE_DATA if module.get("rhel_major_version", 0) == major_version]
    return {
        "meta": {"total": len(modules), "count": len(modules)},
        "data": sorted(item["module_name"] for item in modules),
    }


@router.get("/{major_version}/{module_name}", response_model=AppStreamsResponse)
async def get_module(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
    module_name: t.Annotated[str, Path(description="Module name")],
):
    if data := [module for module in MODULE_DATA if module.get("rhel_major_version", 0) == major_version]:
        if modules := sorted(item for item in data if item.get("module_name") == module_name):
            return {"meta": {"total": len(modules), "count": len(modules)}, "data": modules}

    raise HTTPException(
        status_code=404,
        detail=f"No modules found with name '{module_name}'",
    )


## Relevant ##
relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams"],
)


@relevant.get("/", response_model=AppStreamsResponse)
async def get_relevant_app_streams(result: t.Annotated[t.Any, Depends(get_app_streams)]):
    return result
