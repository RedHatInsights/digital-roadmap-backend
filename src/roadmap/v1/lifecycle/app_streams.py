import logging
import typing as t

from collections import defaultdict
from datetime import date
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi.exceptions import HTTPException
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import model_validator
from sqlalchemy.ext.asyncio.result import AsyncResult

from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import query_host_inventory
from roadmap.common import sort_attrs
from roadmap.common import streams_lt
from roadmap.data.app_streams import APP_STREAM_MODULES_BY_KEY
from roadmap.data.app_streams import APP_STREAM_MODULES_PACKAGES
from roadmap.data.app_streams import APP_STREAM_PACKAGES
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.data.app_streams import OS_MAJORS_BY_APP_NAME
from roadmap.models import _calculate_support_status
from roadmap.models import Meta
from roadmap.models import SupportStatus


logger = logging.getLogger("uvicorn.error")

Date = t.Annotated[str | date | None, AfterValidator(ensure_date)]
MajorVersion = t.Annotated[int | None, Path(description="Major version number", ge=8, le=10)]


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


class RelevantAppStream(BaseModel):
    """App stream module or package with calculated support status."""

    name: str
    application_stream_name: str
    display_name: str
    os_major: int | None
    os_minor: int | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    count: int
    rolling: bool = False
    support_status: SupportStatus = SupportStatus.unknown
    impl: AppStreamImplementation
    systems: list[UUID]
    related: bool = False

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


@router.get(
    "",
    summary="Lifecycle dates for app stream modules and packages",
    response_model=AppStreamsResponse,
)
async def get_app_streams(filter_params: AppStreamFilter):
    result = APP_STREAM_MODULES_PACKAGES
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get(
    "/{major_version}",
    summary="App stream modules and packages for a specific RHEL version",
    response_model=AppStreamsResponse,
)
async def get_major_version(
    major_version: MajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES_PACKAGES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get(
    "/{major_version}/packages",
    summary="List package names for a specific RHEL version",
    response_model=AppStreamsNamesResponse,
)
async def get_app_stream_item_names(
    major_version: MajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES_PACKAGES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted({item.name for item in result}),
    }


@router.get(
    "/{major_version}/streams",
    summary="List app stream names for a specific RHEL version",
    response_model=AppStreamsNamesResponse,
)
async def get_app_stream_names(
    major_version: MajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES_PACKAGES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted({item.application_stream_name for item in result}),
    }


class AppStreamKey(BaseModel):
    """Wraps AppStreamEntitys to facilitate grouping by name."""

    name: str
    app_stream_entity: AppStreamEntity

    def __hash__(self):
        return hash(
            (
                self.name,
                self.app_stream_entity.display_name,
                self.app_stream_entity.application_stream_name,
                self.app_stream_entity.os_major,
                self.app_stream_entity.os_minor,
                self.app_stream_entity.start_date,
                self.app_stream_entity.end_date,
                self.app_stream_entity.impl,
                self.app_stream_entity.rolling,
            )
        )

    def __eq__(self, other):
        return isinstance(other, AppStreamKey) and self.__hash__() == other.__hash__()


def related_app_streams(app_streams: t.Iterable[AppStreamKey]) -> set[AppStreamKey]:
    """Return unique list of related apps that do not appear in app_streams."""
    relateds = set()
    for app_stream_key in app_streams:
        for app in APP_STREAM_MODULES_PACKAGES:
            add = False
            if app.display_name == app_stream_key.app_stream_entity.display_name:
                if app.start_date and app_stream_key.app_stream_entity.start_date:
                    if app.start_date > app_stream_key.app_stream_entity.start_date:
                        add = True
                elif streams_lt(app_stream_key.app_stream_entity.stream, app.stream):
                    if app.end_date is None or app.end_date > date.today():
                        add = True
            if add:
                relateds.add(AppStreamKey(app_stream_entity=app, name=app_stream_key.name))

    return relateds.difference(app_streams)


async def systems_by_app_stream(
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[AsyncResult, Depends(query_host_inventory)],
) -> dict[AppStreamKey, list[UUID]]:
    """Return a mapping of AppStreams to ids of systems using that stream."""
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
        dnf_modules = system_profile.get("dnf_modules", [])

        if not dnf_modules:
            missing["dnf_modules"] += 1

        module_app_streams = app_streams_from_modules(dnf_modules, os_major)
        package_app_streams = app_streams_from_packages(system_profile.get("installed_packages", ""), os_major)

        if not package_app_streams:
            missing["package_names"] += 1

        app_streams = module_app_streams | package_app_streams

        system_id = system["id"]
        for app_stream in app_streams:
            systems_by_stream[app_stream].append(system_id)

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    return systems_by_stream


def app_streams_from_modules(
    dnf_modules: list[dict],
    os_major: str,
) -> set[AppStreamKey]:
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

        app_streams.add(AppStreamKey(app_stream_entity=matched_module, name=name))

    return app_streams


class StringPackage(BaseModel, frozen=True):
    name: str
    major: str

    @classmethod
    def from_string(cls, s):
        name, separator, major = s.partition(":")
        if not separator:
            # Missing ':' in the expected package name. Partition on '-' instead.
            #   Example: cairo-1.15.12-3.el8.x86_64
            name, separator, major = s.partition("-")

        name = name.rsplit("-", 1)[0]
        major = major.split(".")[0]
        return cls(name=name, major=major)


def app_streams_from_packages(
    package_names_string: list[str],
    os_major: str,
) -> set[AppStreamKey]:
    packages = set(StringPackage.from_string(s) for s in package_names_string)
    app_streams = set()
    for package in packages:
        if app_stream_package := APP_STREAM_PACKAGES.get(package.name):
            if app_stream_package.os_major == os_major and app_stream_package.stream.split(".")[0] == package.major:
                app_streams.add(
                    AppStreamKey(app_stream_entity=app_stream_package, name=app_stream_package.application_stream_name)
                )
    return app_streams


## Relevant ##
relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams"],
)


@relevant.get(
    "",
    summary="App streams based on hosts in inventory",
    response_model=RelevantAppStreamsResponse,
)
async def get_relevant_app_streams(
    systems_by_stream: t.Annotated[dict[AppStreamKey, list[UUID]], Depends(systems_by_app_stream)],
    related: bool = False,
):
    relevant_app_streams = []
    for app_stream, systems in systems_by_stream.items():
        # Omit rolling app streams.
        if app_stream.app_stream_entity.rolling:
            continue

        try:
            relevant_app_streams.append(
                RelevantAppStream(
                    name=app_stream.name,
                    display_name=app_stream.app_stream_entity.display_name,
                    application_stream_name=app_stream.app_stream_entity.application_stream_name,
                    start_date=app_stream.app_stream_entity.start_date,
                    end_date=app_stream.app_stream_entity.end_date,
                    os_major=app_stream.app_stream_entity.os_major,
                    os_minor=app_stream.app_stream_entity.os_minor,
                    impl=app_stream.app_stream_entity.impl,
                    count=len(systems),
                    rolling=app_stream.app_stream_entity.rolling,
                    systems=systems,
                    related=False,
                )
            )
        except Exception as exc:
            raise HTTPException(detail=str(exc), status_code=400)

    if related:
        for app_stream in related_app_streams(systems_by_stream.keys()):
            # Omit rolling app streams.
            if app_stream.app_stream_entity.rolling:
                continue

            try:
                relevant_app_streams.append(
                    RelevantAppStream(
                        name=app_stream.name,
                        display_name=app_stream.app_stream_entity.display_name,
                        application_stream_name=app_stream.app_stream_entity.application_stream_name,
                        start_date=app_stream.app_stream_entity.start_date,
                        end_date=app_stream.app_stream_entity.end_date,
                        os_major=app_stream.app_stream_entity.os_major,
                        os_minor=app_stream.app_stream_entity.os_minor,
                        impl=app_stream.app_stream_entity.impl,
                        count=0,
                        rolling=app_stream.app_stream_entity.rolling,
                        systems=[],
                        related=True,
                    )
                )
            except Exception as exc:
                raise HTTPException(detail=str(exc), status_code=400)

    return {
        "meta": {
            "count": len(relevant_app_streams),
            "total": sum(item.count for item in relevant_app_streams),
        },
        "data": sorted(relevant_app_streams, key=sort_attrs("name", "os_major", "os_minor")),
    }
