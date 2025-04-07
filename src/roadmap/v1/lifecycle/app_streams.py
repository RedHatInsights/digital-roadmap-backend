import logging
import typing as t

from collections import defaultdict
from datetime import date

from fastapi import APIRouter
from fastapi import Header
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from fastapi.params import Depends
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from roadmap.common import ensure_date
from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.common import sort_attrs
from roadmap.data import APP_STREAM_MODULES
from roadmap.data.app_streams import APP_STREAM_MODULES_PACKAGES
from roadmap.data.app_streams import APP_STREAM_PACKAGES
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.models import _calculate_support_status
from roadmap.models import LifecycleType
from roadmap.models import Meta
from roadmap.models import SupportStatus


logger = logging.getLogger("uvicorn.error")

Date = t.Annotated[str | date | None, AfterValidator(ensure_date)]
RHELMajorVersion = t.Annotated[int, Path(description="Major RHEL version", ge=8, le=10)]


def get_rolling_value(name: str, stream: str, os_major: int) -> bool:
    for item in APP_STREAM_MODULES:
        if (name, os_major) == (item.name, item.os_major):
            if item.stream == stream:
                return item.rolling

    logger.debug(f"No match for rolling RHEL {os_major} {name} {stream}")
    return False


def get_module_os_major_versions(name: str) -> set[int]:
    matches = set()
    for item in APP_STREAM_MODULES:
        if item.name == name:
            matches.add(item.os_major)

    return matches


async def filter_app_stream_results(data, filter_params):
    if name := filter_params.get("name"):
        data = [item for item in data if name.lower() in item.name.lower()]

    if kind := filter_params.get("kind"):
        data = [item for item in data if kind == item.impl]

    if application_stream_name := filter_params.get("application_stream_name"):
        data = [item for item in data if application_stream_name.lower() in item.application_stream_name.lower()]

    return data


async def filter_params(
    name: t.Annotated[str | None, Query(description="Module or package name")] = None,
    kind: AppStreamImplementation | None = None,
    application_stream_name: t.Annotated[str | None, Query(description="App Stream name")] = None,
):
    return {"name": name, "kind": kind, "application_stream_name": application_stream_name}


AppStreamFilter = t.Annotated[dict, Depends(filter_params)]


class AppStreamCount(BaseModel):
    """All these things must match in order for a module to be considered the same."""

    model_config = ConfigDict(frozen=True)

    name: str
    os_major: int | None
    os_minor: int | None = None
    os_lifecycle: LifecycleType | None
    stream: str
    impl: AppStreamImplementation
    rolling: bool = False


class RelevantAppStream(BaseModel):
    """App stream module or package with calculated support status."""

    name: str
    os_major: int | None
    os_minor: int | None = None
    os_lifecycle: LifecycleType | None
    stream: str
    start_date: Date | None = None
    end_date: Date | None = None
    count: int
    rolling: bool = False
    support_status: SupportStatus = SupportStatus.unknown
    impl: AppStreamImplementation

    @model_validator(mode="after")
    def update_support_status(self):
        """Validator for setting status."""
        today = date.today()
        self.support_status = _calculate_support_status(
            start_date=self.start_date, end_date=self.end_date, current_date=today
        )

        return self


class RelevantAppStreamsResponse(BaseModel):
    meta: Meta
    data: list[RelevantAppStream]


class AppStreamsNamesResponse(BaseModel):
    meta: Meta
    data: list[str]


class AppStreamsResponse(BaseModel):
    meta: Meta
    data: list[AppStreamEntity]


router = APIRouter(
    prefix="/app-streams",
    tags=["App Streams"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=AppStreamsResponse)
async def get_app_streams(filter_params: AppStreamFilter):
    result = APP_STREAM_MODULES_PACKAGES
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get("/{major_version}", response_model=AppStreamsResponse)
async def get_major_version(
    major_version: RHELMajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES_PACKAGES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get("/{major_version}/names", response_model=AppStreamsNamesResponse)
async def get_app_stream_item_names(
    major_version: RHELMajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES_PACKAGES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted({item.name for item in result}),
    }


## Relevant ##
relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams"],
)


@relevant.get("/", response_model=RelevantAppStreamsResponse)
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
        if count_key.rolling:
            # Omit rolling app streams
            continue

        try:
            value_to_add = RelevantAppStream(
                name=count_key.name,
                stream=count_key.stream,
                os_major=count_key.os_major,
                os_minor=count_key.os_minor,
                os_lifecycle=count_key.os_lifecycle,
                impl=count_key.impl,
                count=count,
                rolling=count_key.rolling,
            )
            response.append(value_to_add)
        except Exception as exc:
            raise HTTPException(detail=str(exc), status_code=400)

    return {
        "meta": {
            "count": len(module_count),
            "total": sum(item.count for item in response),
        },
        "data": sorted(response, key=sort_attrs("name", "os_major", "os_minor", "os_lifecycle")),
    }
