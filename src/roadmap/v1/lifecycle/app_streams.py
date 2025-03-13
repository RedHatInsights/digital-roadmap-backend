import logging
import typing as t

from collections import defaultdict
from datetime import date
from enum import StrEnum

from fastapi import APIRouter
from fastapi import Header
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from roadmap.common import ensure_date
from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.common import sort_null_version
from roadmap.data import APP_STREAM_MODULES
from roadmap.data.app_streams import APP_STREAM_PACKAGES
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import LifecycleType
from roadmap.models import Meta
from roadmap.models import SupportStatus


logger = logging.getLogger("uvicorn.error")

Date = t.Annotated[str | date | None, AfterValidator(ensure_date)]


def get_rolling_value(name: str, stream: str, os_major: int) -> bool:
    for item in APP_STREAM_MODULES:
        if (name, os_major) == (item["module_name"], item["rhel_major_version"]):
            for module_stream in item["streams"]:
                if module_stream["stream"] == stream:
                    return module_stream["rolling"]

    logger.debug(f"No match for rolling RHEL {os_major} {name} {stream}")
    return False


def get_module_os_major_versions(name: str) -> set[int]:
    matches = set()
    for item in APP_STREAM_MODULES:
        if item["module_name"] == name:
            matches.add(item["rhel_major_version"])

    return matches


class AppStreamImplementation(StrEnum):
    scl = "scl"
    package = "package"
    module = "dnf_module"


class AppStreamCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    os_major: int | None
    os_minor: int | None = None
    os_lifecycle: LifecycleType | None
    stream: str
    impl: AppStreamImplementation
    rolling: bool = False


class AppStream(BaseModel):
    name: str
    os_major: int | None
    os_minor: int | None = None
    os_lifecycle: LifecycleType | None
    stream: str
    start_date: Date | None = None
    end_date: Date | None = None
    count: int
    rolling: bool = False
    support_status: SupportStatus
    impl: AppStreamImplementation

    # Module validators are run in the order they are defined.
    @model_validator(mode="after")
    def set_dates(self):  # noqa: C901
        """Set end_date based on rolling status, OS major/minor, and lifecycle"""

        # If not rolling, use package/module start/end dates
        # If it is rolling, use OS start/end dates
        #   need to know the lifecycle type

        if self.rolling:
            os_key = f"{self.os_major}{'.' + str(self.os_minor) if self.os_minor is not None else ''}"

            # Start date
            if self.start_date is None:
                try:
                    self.start_date = OS_LIFECYCLE_DATES[os_key].start
                except KeyError:
                    logger.error(f"Missing OS lifecycle data for {self.os_major}.{self.os_minor}")
                    self.start_date = "Unknown"

            # End date
            lifecycle_attr = "end"
            if self.os_lifecycle and self.os_lifecycle is not LifecycleType.mainline:
                lifecycle_attr += f"_{self.os_lifecycle.lower()}"

            try:
                self.end_date = getattr(OS_LIFECYCLE_DATES[os_key], lifecycle_attr)
            except KeyError:
                logger.error(f"Missing OS lifecycle data for {self.os_major}.{self.os_minor}")
                self.end_date = "Unknown"

        else:
            if self.impl is AppStreamImplementation.package:
                for app_stream_package in APP_STREAM_PACKAGES.values():
                    if (app_stream_package.application_stream_name, app_stream_package.os_major) == (
                        self.name,
                        self.os_major,
                    ):
                        self.start_date = app_stream_package.start_date
                        self.end_date = app_stream_package.end_date
                        break

            elif self.impl is AppStreamImplementation.module:
                for app_stream_module in APP_STREAM_MODULES:
                    if (app_stream_module["module_name"], app_stream_module["rhel_major_version"]) == (
                        self.name,
                        self.os_major,
                    ):
                        for stream in app_stream_module["streams"]:
                            if stream["stream"] == self.stream:
                                self.start_date = stream["start_date"]
                                self.end_date = stream["end_date"]
                                break

        return self


class AppStreamsResponse(BaseModel):
    meta: Meta
    data: list[AppStream]


class AppStreamsNamesResponse(BaseModel):
    meta: Meta
    data: list[str]


class ModulesResponse(BaseModel):
    meta: Meta
    data: list[dict]


router = APIRouter(
    prefix="/app-streams",
    tags=["App Streams"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=ModulesResponse)
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


@router.get("/{major_version}", response_model=ModulesResponse)
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


@router.get("/{major_version}/{module_name}", response_model=ModulesResponse)
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

        app_stream_counts = set()
        for dnf_module in dnf_modules:
            if "perl" in dnf_module["name"].lower():
                # Bug with Perl data currently. Omit for now.
                continue

            if os_major not in get_module_os_major_versions(dnf_module["name"]):
                continue

            rolling = get_rolling_value(dnf_module["name"], dnf_module["stream"], os_major)
            count_key = AppStreamCount(
                name=dnf_module["name"],
                stream=dnf_module["stream"],
                os_major=os_major,
                os_minor=os_minor if rolling else None,
                os_lifecycle=os_lifecycle if rolling else None,
                rolling=rolling,
                impl=AppStreamImplementation.module,
            )
            app_stream_counts.add(count_key)

        package_names = {pkg.split(":")[0].rsplit("-", 1)[0] for pkg in system_profile.get("installed_packages", "")}
        for package_name in package_names:
            if app_stream_package := APP_STREAM_PACKAGES.get(package_name):
                # Ensure os_major on app stream package is same as os_major of system
                # Before creating a count key, make sure it's an actual package available for that system
                if app_stream_package.os_major != os_major:
                    continue

                count_key = AppStreamCount(
                    name=app_stream_package.application_stream_name,
                    stream=app_stream_package.stream,
                    os_major=os_major,
                    os_minor=os_minor if app_stream_package.rolling else None,
                    # TODO: Ask Brian if we want rolling releases to be displayed individually
                    #   Setting os_minor=None for rolling streams will combine all items into one result
                    #   This probably looks better and makes more sense.
                    # os_minor=os_minor,
                    os_lifecycle=os_lifecycle if app_stream_package.rolling else None,
                    rolling=app_stream_package.rolling,
                    impl=AppStreamImplementation.package,
                )
                app_stream_counts.add(count_key)

        for app_stream_count in app_stream_counts:
            module_count[app_stream_count] += 1

    # Build response
    response = []
    for count_key, count in module_count.items():
        try:
            value_to_add = AppStream(
                name=count_key.name,
                stream=count_key.stream,
                os_major=count_key.os_major,
                os_minor=count_key.os_minor,
                os_lifecycle=count_key.os_lifecycle,
                impl=count_key.impl,
                count=count,
                rolling=count_key.rolling,
                support_status=SupportStatus.supported,  # TODO: Calculate support status
            )
            response.append(value_to_add)
        except Exception as exc:
            raise HTTPException(detail=str(exc), status_code=400)

    return {
        "meta": {
            "count": len(module_count),
        },
        "data": sorted(response, key=sort_null_version("name", "stream", "os_major", "os_minor", "os_lifecycle")),
    }
