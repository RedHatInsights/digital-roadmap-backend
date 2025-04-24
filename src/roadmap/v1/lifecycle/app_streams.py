import logging
import typing as t

from collections import defaultdict
from datetime import date
from uuid import UUID

from fastapi import APIRouter
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from fastapi.params import Depends
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.common import sort_attrs
from roadmap.data.app_streams import APP_STREAM_MODULES_BY_KEY
from roadmap.data.app_streams import APP_STREAM_MODULES_PACKAGES
from roadmap.data.app_streams import APP_STREAM_PACKAGES
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.data.app_streams import OS_MAJORS_BY_APP_NAME
from roadmap.models import _calculate_support_status
from roadmap.models import LifecycleType
from roadmap.models import Meta
from roadmap.models import SupportStatus


logger = logging.getLogger("uvicorn.error")

Date = t.Annotated[str | date | None, AfterValidator(ensure_date)]
RHELMajorVersion = t.Annotated[int, Path(description="Major RHEL version", ge=8, le=10)]


def get_rolling_value(name: str, stream: str, os_major: int) -> bool:
    try:
        return APP_STREAM_MODULES_BY_KEY[(name, os_major, stream)].rolling
    except KeyError:
        logger.debug(f"No match for rolling RHEL {os_major} {name} {stream}")
        return False


def get_module_os_major_versions(name: str) -> set[int]:
    return OS_MAJORS_BY_APP_NAME.get(name, set())


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


class AppStreamKey(BaseModel):
    """All these things must match in order for a module to be considered the same."""

    model_config = ConfigDict(frozen=True)

    name: str
    application_stream_name: str
    os_major: int | None
    os_minor: int | None = None
    os_lifecycle: LifecycleType | None
    stream: str
    start_date: Date | None = None
    end_date: Date | None = None
    impl: AppStreamImplementation
    rolling: bool = False


class RelevantAppStream(BaseModel):
    """App stream module or package with calculated support status."""

    name: str
    application_stream_name: str
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
    systems: list[UUID]

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


@router.get("", response_model=AppStreamsResponse)
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


@router.get("/{major_version}/packages", response_model=AppStreamsNamesResponse)
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


@router.get("/{major_version}/streams", response_model=AppStreamsNamesResponse)
async def get_app_stream_names(
    major_version: RHELMajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES_PACKAGES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted({item.application_stream_name for item in result}),
    }


## Relevant ##
relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams"],
)


@relevant.get("", response_model=RelevantAppStreamsResponse)
async def get_relevant_app_streams(  # noqa: C901
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[t.Any, Depends(query_host_inventory)],
):
    logger.info(f"Getting relevant app streams for {org_id or 'UNKNOWN'}")

    missing = defaultdict(int)
    systems_by_stream = defaultdict(list)
    async for system in systems.mappings():
        system_profile = system.get("system_profile_facts")
        if not system_profile:
            missing["system_profile"] += 1
            continue

        if "RHEL" != system_profile.get("operating_system", {}).get("name"):
            missing["os"] += 1
            continue

        os_major = system_profile.get("operating_system", {}).get("major")
        os_minor = system_profile.get("operating_system", {}).get("minor")
        os_lifecycle = get_lifecycle_type(system_profile.get("installed_products", [{}]))
        dnf_modules = system_profile.get("dnf_modules", [])

        if not dnf_modules:
            missing["dnf_modules"] += 1

        module_app_streams = app_streams_from_modules(dnf_modules, os_major, os_minor, os_lifecycle)
        package_app_streams = app_streams_from_packages(
            system_profile.get("installed_packages", ""), os_major, os_minor, os_lifecycle
        )

        if not package_app_streams:
            missing["package_names"] += 1

        app_streams = module_app_streams | package_app_streams

        system_id = system["id"]
        for app_stream in app_streams:
            systems_by_stream[app_stream].append(system_id)

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    response = []
    for app_stream, systems in systems_by_stream.items():
        # Omit rolling app streams.
        if app_stream.rolling:
            continue

        try:
            response.append(
                RelevantAppStream(
                    name=app_stream.name,
                    application_stream_name=app_stream.application_stream_name,
                    stream=app_stream.stream,
                    start_date=app_stream.start_date,
                    end_date=app_stream.end_date,
                    os_major=app_stream.os_major,
                    os_minor=app_stream.os_minor,
                    os_lifecycle=app_stream.os_lifecycle,
                    impl=app_stream.impl,
                    count=len(systems),
                    rolling=app_stream.rolling,
                    systems=systems,
                )
            )
        except Exception as exc:
            raise HTTPException(detail=str(exc), status_code=400)

    return {
        "meta": {
            "count": len(response),
            "total": sum(item.count for item in response),
        },
        "data": sorted(response, key=sort_attrs("name", "os_major", "os_minor", "os_lifecycle")),
    }


def app_streams_from_modules(dnf_modules: list[dict], os_major: str, os_minor: str, os_lifecycle: str):
    """Return a set of normalized AppStreamKey objects for the given modules"""
    app_streams = set()
    for dnf_module in dnf_modules:
        if "perl" in dnf_module["name"].lower():
            # Bug with Perl data currently. Omit for now.
            continue

        name = dnf_module["name"]
        if os_major not in get_module_os_major_versions(name):
            continue

        stream = dnf_module["stream"]
        matched_module = APP_STREAM_MODULES_BY_KEY.get((name, os_major, stream))
        if not matched_module:
            logger.debug(f"Did not find matching app stream module {name}, {os_major}, {stream}")
            matched_module = AppStreamEntity(
                name=name,
                stream=stream,
                start_date=None,
                end_date=None,
                application_stream_name="Unknown",
                impl=AppStreamImplementation.module,
            )

        rolling = get_rolling_value(name, stream, os_major)
        app_key = AppStreamKey(
            name=name,
            stream=stream,
            start_date=matched_module.start_date,
            end_date=matched_module.end_date,
            application_stream_name=matched_module.application_stream_name,
            os_major=os_major,
            os_minor=os_minor if rolling else None,
            os_lifecycle=os_lifecycle if rolling else None,
            rolling=rolling,
            impl=AppStreamImplementation.module,
        )
        app_streams.add(app_key)

    return app_streams


def app_streams_from_packages(package_names_string: str, os_major: str, os_minor: str, os_lifecycle: str):
    package_names = {pkg.split(":")[0].rsplit("-", 1)[0] for pkg in package_names_string}

    app_streams = set()
    for package_name in package_names:
        if app_stream_package := APP_STREAM_PACKAGES.get(package_name):
            # Ensure os_major on app stream package is same as os_major of system
            # Before creating an AppStreamKey, make sure it's an actual package available for that system
            if app_stream_package.os_major != os_major:
                continue

            app_key = AppStreamKey(
                name=app_stream_package.application_stream_name,
                application_stream_name=app_stream_package.application_stream_name,
                stream=app_stream_package.stream,
                start_date=app_stream_package.start_date,
                end_date=app_stream_package.end_date,
                os_major=os_major,
                os_minor=os_minor if app_stream_package.rolling else None,
                os_lifecycle=os_lifecycle if app_stream_package.rolling else None,
                rolling=app_stream_package.rolling,
                impl=AppStreamImplementation.package,
            )
            app_streams.add(app_key)

    return app_streams
