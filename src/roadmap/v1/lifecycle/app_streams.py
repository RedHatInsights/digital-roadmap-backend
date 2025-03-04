import logging
import typing as t

from collections import defaultdict

from fastapi import APIRouter
from fastapi import Header
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from pydantic import BaseModel

from roadmap.common import query_host_inventory
from roadmap.data import APP_STREAM_MODULES
from roadmap.models import AppStreamCount
from roadmap.models import LifecycleType
from roadmap.models import Meta


logger = logging.getLogger("uvicorn.error")


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
        result = [module for module in APP_STREAM_MODULES if name.lower() in module["module_name"].lower()]

        return {
            "meta": {"total": len(result), "count": len(result)},
            "data": result,
        }

    return {
        "meta": {"total": len(APP_STREAM_MODULES), "count": len(APP_STREAM_MODULES)},
        "data": [module for module in APP_STREAM_MODULES],
    }


@router.get("/{major_version}", response_model=AppStreamsResponse)
async def get_major_version(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
):
    modules = [module for module in APP_STREAM_MODULES if module.get("rhel_major_version", 0) == major_version]
    return {
        "meta": {"total": len(modules), "count": len(modules)},
        "data": modules,
    }


@router.get("/{major_version}/names", response_model=AppStreamsNamesResponse)
async def get_module_names(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
):
    modules = [module for module in APP_STREAM_MODULES if module.get("rhel_major_version", 0) == major_version]
    return {
        "meta": {"total": len(modules), "count": len(modules)},
        "data": sorted(item["module_name"] for item in modules),
    }


@router.get("/{major_version}/{module_name}", response_model=AppStreamsResponse)
async def get_module(
    major_version: t.Annotated[int, Path(description="Major RHEL version", gt=1, le=200)],
    module_name: t.Annotated[str, Path(description="Module name")],
):
    if data := [module for module in APP_STREAM_MODULES if module.get("rhel_major_version", 0) == major_version]:
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


def is_rolling(name: str, stream: str, os_major: int) -> bool | None | str:
    for module in APP_STREAM_MODULES:
        if (module["module_name"], module["rhel_major_version"]) == (name, os_major):
            for s in module["streams"]:
                if s["stream"] == stream:
                    # Match!
                    # Unknown values will be None
                    return s["rolling"]

    # No match
    return False


@relevant.get("/", response_model=AppStreamsResponse)
async def get_relevant_app_streams(  # noqa: C901
    authorization: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    user_agent: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
):
    headers = {
        "Authorization": authorization,
        "User-Agent": user_agent,
        "X-RH-Identity": x_rh_identity,
    }
    module_count = defaultdict(int)
    inventory_result = await query_host_inventory(headers=headers)
    module_names = [
        (item["name"], item["stream"])
        for result in inventory_result["results"]
        for item in result.get("system_profile", {}).get("dnf_modules", {})
    ]
    logger.debug(f"Modules: {module_names}")
    for result in inventory_result.get("results", []):
        system_profile = result.get("system_profile")
        if not system_profile:
            logger.info(f"Unable to get relevant systems due to missing system profile. ID={result.get('id')}")
            continue

        name = system_profile.get("operating_system", {}).get("name")
        if name is None:
            logger.info("Unable to get relevant systems due to missing OS from system profile")
            continue

        if (dnf_modules := system_profile.get("dnf_modules", [])) is None:
            logger.info("Unable to get relevant systems due to missing OS from system profile")
            continue

        os_major = system_profile.get("operating_system", {}).get("major")
        os_minor = system_profile.get("operating_system", {}).get("minor")

        for module in dnf_modules:
            rolling = is_rolling(module["name"], module["stream"], os_major)
            count_key = AppStreamCount(
                name=module["name"],
                stream=module["stream"],
                os_major=os_major,
                os_minor=os_minor if rolling else None,
                os_lifecycle=LifecycleType.mainline if rolling else None,
            )
            logger.debug(count_key)
            module_count[count_key] += 1

    # Build response
    # Look at RHEL major, then module_name, stream
    #   If those match, add to response and add count

    response = []
    for module, count in module_count.items():
        for m in APP_STREAM_MODULES:
            if (module.os_major, module.name) == (m["rhel_major_version"], m["module_name"]):
                for stream in m["streams"]:
                    if module.stream == stream["stream"]:
                        # Got it!
                        # Include in response
                        # TODO: Get correct dates
                        value_to_add = {
                            "name": module.name,
                            "stream": module.stream,
                            "os_major": module.os_major,
                            "os_minor": module.os_minor,
                            "os_lifecycle": module.os_lifecycle,
                            "start_date": stream["start_date"],  # TODO: Get correct dates
                            "end_date": stream["end_date"],  # TODO: Get correct dates
                            "count": count,
                            "rolling": stream["rolling"],
                        }
                        response.append(value_to_add)

    return {
        "meta": {
            "total": sum(module_count.values()),
            "count": len(module_count),
        },
        "data": response,
    }
