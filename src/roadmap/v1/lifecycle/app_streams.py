import logging
import typing as t

from collections import defaultdict
from datetime import date

from fastapi import APIRouter
from fastapi import Header
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from pydantic import BaseModel
from pydantic import model_validator

from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.data import APP_STREAM_MODULES
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import AppStreamCount
from roadmap.models import LifecycleType
from roadmap.models import Meta
from roadmap.models import SupportStatus


logger = logging.getLogger("uvicorn.error")


class AppStream(BaseModel):
    name: str
    stream: str
    os_major: int
    os_minor: int | None = None
    os_lifecycle: LifecycleType
    start_date: date
    end_date: date
    count: int
    rolling: bool
    support_status: SupportStatus

    @model_validator(mode="after")
    def set_end_date(self):
        """Set end_date based on rolling status, OS major/minor, and lifecycle"""
        if self.rolling:
            lifecycle_attr = "end"
            if self.os_lifecycle is not LifecycleType.mainline:
                lifecycle_attr += f"_{self.os_lifecycle.lower()}"

            os_key = f"{self.os_major}{'.' + str(self.os_minor) if self.os_minor is not None else ''}"
            try:
                self.end_date = getattr(OS_LIFECYCLE_DATES[os_key], lifecycle_attr)
            except KeyError:
                logger.error(f"Missing OS lifecycle data for {self.os_major}.{self.os_minor}")
                self.end_date = date(1111, 11, 11)
                return self

        return self


class AppStreamsResponse(BaseModel):
    meta: Meta
    data: list[AppStream]


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

    # Get a count of each module and package based on OS and OS lifecycle
    for system in inventory_result.get("results", []):
        system_profile = system.get("system_profile")
        if not system_profile:
            logger.info(f"Unable to get relevant systems due to missing system profile. ID={system.get('id')}")
            continue

        # Make sure the system is RHEL
        name = system_profile.get("operating_system", {}).get("name")
        if name != "RHEL":
            logger.info("Unable to get relevant systems due to missing OS from system profile")
            continue

        os_major = system_profile.get("operating_system", {}).get("major")
        os_minor = system_profile.get("operating_system", {}).get("minor")
        os_lifecycle = get_lifecycle_type(system_profile.get("installed_products", [{}]))
        dnf_modules = system_profile.get("dnf_modules", [])

        for module in dnf_modules:
            rolling = is_rolling(module["name"], module["stream"], os_major)
            count_key = AppStreamCount(
                name=module["name"],
                stream=module["stream"],
                os_major=os_major,
                os_minor=os_minor,
                os_lifecycle=os_lifecycle,
                rolling=rolling,
            )
            logger.debug(count_key)
            module_count[count_key] += 1

    # Build response
    # Look at RHEL major, then module_name, stream
    #   If those match, add to response and add count
    response = []
    for count_key, count in module_count.items():
        for module in APP_STREAM_MODULES:
            if (count_key.os_major, count_key.name) == (module["rhel_major_version"], module["module_name"]):
                try:
                    for stream in module["streams"]:
                        if count_key.stream == stream["stream"]:
                            # Got it!
                            # Include in response
                            value_to_add = AppStream(
                                name=count_key.name,
                                stream=count_key.stream,
                                os_major=count_key.os_major,
                                os_minor=count_key.os_minor,
                                os_lifecycle=count_key.os_lifecycle,
                                start_date=stream["start_date"],
                                end_date=stream["end_date"],
                                count=count,
                                rolling=stream["rolling"],
                                support_status=SupportStatus.supported,  # TODO: Calculate support status
                            )
                            response.append(value_to_add)
                except Exception:
                    logger.debug(f"{stream.get('name', 'name')} {stream.get('end_date', 'end_date')}")
    return {
        "meta": {
            "total": sum(module_count.values()),
            "count": len(module_count),
        },
        "data": response,
    }
