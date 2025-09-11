import functools
import logging
import typing as t

from collections import defaultdict
from datetime import date
from enum import auto
from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi.exceptions import HTTPException
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from sqlalchemy.ext.asyncio.result import AsyncResult

from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import query_host_inventory
from roadmap.common import rhel_major_minor
from roadmap.common import sort_attrs
from roadmap.common import streams_lt
from roadmap.data import APP_STREAM_MODULES
from roadmap.data import APP_STREAM_MODULES_BY_KEY
from roadmap.data import APP_STREAM_MODULES_PACKAGES
from roadmap.data import APP_STREAM_PACKAGES
from roadmap.data import APP_STREAMS
from roadmap.data import OS_MAJORS_BY_APP_NAME
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.data.app_streams import AppStreamType
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import _calculate_support_status
from roadmap.models import _get_system_uuids
from roadmap.models import Meta
from roadmap.models import SupportStatus
from roadmap.models import SystemInfo


logger = logging.getLogger("uvicorn.error")

Date = t.Annotated[str | date, AfterValidator(ensure_date)]
MajorVersion = t.Annotated[int, Path(description="Major version number", ge=8, le=10)]


async def filter_app_stream_results(data, filter_params):
    if name := filter_params.get("name"):
        name = name.casefold()
        data = [item for item in data if name in item.name]

    if kind := filter_params.get("kind"):
        data = [item for item in data if kind == item.impl]

    if application_stream_name := filter_params.get("application_stream_name"):
        application_stream_name = application_stream_name.casefold()
        data = [item for item in data if application_stream_name in item.application_stream_name.casefold()]

    if application_stream_type := filter_params.get("application_stream_type"):
        data = [item for item in data if application_stream_type == (item.application_stream_type or "")]

    return data


async def filter_params(
    name: t.Annotated[str | None, Query(description="Module or package name")] = None,
    kind: AppStreamImplementation | None = None,
    application_stream_name: t.Annotated[str | None, Query(description="App Stream name")] = None,
    application_stream_type: t.Annotated[AppStreamType | None, Query(description="App Stream type")] = None,
):
    return {
        "name": name,
        "kind": kind,
        "application_stream_name": application_stream_name,
        "application_stream_type": application_stream_type,
    }


AppStreamFilter = t.Annotated[dict, Depends(filter_params)]


class RelevantAppStream(BaseModel):
    """App stream module or package with calculated support status."""

    name: str
    application_stream_name: str
    application_stream_type: AppStreamType | None = None
    display_name: str
    os_major: int | None
    os_minor: int | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    count: int
    rolling: bool = False
    support_status: SupportStatus = SupportStatus.unknown
    systems_detail: set[SystemInfo]
    systems: set[UUID] = Field(default_factory=_get_system_uuids)
    related: bool = False

    @model_validator(mode="after")
    def update_support_status(self):
        """Validator for setting status."""
        today = date.today()
        self.support_status = _calculate_support_status(
            start_date=self.start_date,  # pyright: ignore [reportArgumentType]
            end_date=self.end_date,  # pyright: ignore [reportArgumentType]
            current_date=today,  # pyright: ignore [reportArgumentType]
            months=6,
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


class AppStreamItemsResponse(BaseModel):
    meta: Meta
    data: list[AppStreamEntity]

    @model_validator(mode="after")
    def set_end_date_support_status(self):
        for n in self.data:
            if n.rolling:
                if os := OS_LIFECYCLE_DATES.get(str(n.os_major)):
                    n.end_date = os.end_date

        # Run model validation in order to ensure the support status is accurate.
        #
        # This is run on API response, so this ensures the support status is
        # accurate when the data is on the way out the door and the end date
        # reflects the correct date for rolling app streams.
        #
        # Otherwise, the support status value is what was calculated when
        # the application started and the AppStreamEntity objects were created.
        self.data = [n.model_validate(n) for n in self.data]

        return self


router = APIRouter(
    prefix="/app-streams",
    tags=["App Streams"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "",
    summary="App stream module and package lifecycle information",
    response_model=AppStreamItemsResponse,
)
async def get_app_stream_items(filter_params: AppStreamFilter):
    result = await filter_app_stream_results(APP_STREAM_MODULES_PACKAGES, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get(
    "/streams",
    summary="Application streams lifecycle information",
    response_model=AppStreamsResponse,
)
async def get_app_streams(filter_params: AppStreamFilter):
    result = await filter_app_stream_results(APP_STREAMS, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("display_name")),
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
    result = [item for item in APP_STREAM_MODULES_PACKAGES if item.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get(
    "/{major_version}/modules",
    summary="List app stream modules for a specific RHEL version",
    response_model=AppStreamsResponse,
)
async def get_modules_major_version(
    major_version: MajorVersion,
    filter_params: AppStreamFilter,
):
    result = [module for module in APP_STREAM_MODULES if module.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get(
    "/{major_version}/packages",
    summary="List app stream packages for a specific RHEL version",
    response_model=AppStreamsResponse,
)
async def get_packages_major_version(
    major_version: MajorVersion,
    filter_params: AppStreamFilter,
):
    result = await filter_app_stream_results(APP_STREAM_PACKAGES[major_version].values(), filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("name")),
    }


@router.get(
    "/{major_version}/streams",
    summary="List app streams for a specific RHEL version",
    response_model=AppStreamsResponse,
)
async def get_streams_major_version(
    major_version: MajorVersion,
    filter_params: AppStreamFilter,
):
    result = [stream for stream in APP_STREAMS if stream.os_major == major_version]
    result = await filter_app_stream_results(result, filter_params)

    return {
        "meta": {"total": len(result), "count": len(result)},
        "data": sorted(result, key=sort_attrs("display_name")),
    }


class AppStreamKey(BaseModel):
    """Wraps AppStreamEntitys to facilitate grouping by name."""

    name: str
    app_stream_entity: AppStreamEntity

    def __hash__(self):
        return hash(
            (
                self.app_stream_entity.display_name,
                self.app_stream_entity.application_stream_name,
                self.app_stream_entity.os_major,
                self.app_stream_entity.os_minor,
            )
        )

    def __eq__(self, other):
        return isinstance(other, AppStreamKey) and self.__hash__() == other.__hash__()


class ModuleStatus(StrEnum):
    default = auto()
    enabled = auto()
    installed = auto()


def related_app_streams(app_streams: t.Iterable[AppStreamKey]) -> set[AppStreamKey]:
    """Return unique list of related apps that do not appear in app_streams."""
    relateds = set()
    for app_stream_key in app_streams:
        for app in APP_STREAM_MODULES_PACKAGES:
            add = False
            if app.display_name == app_stream_key.app_stream_entity.display_name:
                if app.start_date and app_stream_key.app_stream_entity.start_date:
                    if app.start_date > app_stream_key.app_stream_entity.start_date:  # pyright: ignore [reportArgumentType, reportOperatorIssue]
                        add = True
                elif streams_lt(app_stream_key.app_stream_entity.stream, app.stream):
                    if app.end_date is None or app.end_date > date.today():  # pyright: ignore [reportArgumentType, reportOperatorIssue]
                        add = True
            if add:
                relateds.add(AppStreamKey(app_stream_entity=app, name=app_stream_key.name))

    return relateds.difference(app_streams)


async def systems_by_app_stream(
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[AsyncResult, Depends(query_host_inventory)],
) -> dict[AppStreamKey, set[SystemInfo]]:
    """Return a mapping of AppStreams to informations about systems using that stream."""
    logger.info(f"Getting relevant app streams for {org_id or 'UNKNOWN'}")

    missing = defaultdict(int)
    systems_by_stream = defaultdict(set)
    module_cache = {}
    package_data = defaultdict(list)
    module_app_streams = set()
    async for system in systems.yield_per(2_000).mappings():
        dnf_modules = system["dnf_modules"] or []
        packages = system["packages"] or []

        try:
            os_major, os_minor = rhel_major_minor(system)
        except ValueError:
            missing["os_version"] += 1
            continue

        if not dnf_modules:
            missing["dnf_modules"] += 1

        if not packages:
            missing["packages"] += 1

        # Store package name, os_major, system ID and display name for later processing outside the loop.
        # This substantially reduces the time it takes for this function to return.
        system_info = SystemInfo(
            id=system["id"], display_name=system["display_name"], os_major=os_major, os_minor=os_minor
        )
        for package in packages:
            package_data[(package, os_major)].append(system_info)

        module_app_streams = app_streams_from_modules(dnf_modules, os_major, module_cache)
        for app_stream in module_app_streams:
            systems_by_stream[app_stream].add(system_info)

    # Now process the packages outside of the host record loop
    for args, systems_info in package_data.items():
        package, os_major = args
        if app_stream := app_stream_from_package(package, os_major):
            systems_by_stream[app_stream].update(systems_info)

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    return systems_by_stream


def app_streams_from_modules(
    dnf_modules: list[dict],
    os_major: int,
    cache: dict[str, AppStreamKey],
) -> set[AppStreamKey]:
    """Return a set of normalized AppStreamKey objects for the given modules"""
    app_streams = set()
    for dnf_module in dnf_modules:
        module_name = dnf_module["name"]
        stream = dnf_module["stream"]
        cache_key = f"{module_name}_{os_major}_{stream}"
        if app_stream_key := cache.get(cache_key):
            app_streams.add(app_stream_key)
            continue

        if "perl" in module_name.casefold():
            # Bug with Perl data currently. Omit for now.
            continue

        if os_major not in OS_MAJORS_BY_APP_NAME.get(module_name, []):
            continue

        module_status = dnf_module.get("status", [])
        if os_major <= 8:
            # RHEL 8 lists all modules in the system profile even if they are not
            # installed or enabled. Omit modules that are not explicitly installed.
            if ModuleStatus.installed not in module_status:
                continue
        elif module_status and ModuleStatus.installed not in module_status:
            # RHEL 9 and later only inclue installed modules in the system profile.
            # Include all modules unless there is a status without "installed".
            continue

        matched_module = APP_STREAM_MODULES_BY_KEY.get((module_name, os_major, stream))
        if not matched_module:
            logger.debug(f"Did not find matching app stream module {module_name} {stream} on RHEL {os_major}")
            matched_module = AppStreamEntity(
                name=module_name,
                stream=stream,
                start_date=None,
                end_date=None,
                application_stream_name=SupportStatus.unknown,
                impl=AppStreamImplementation.module,
            )

        app_stream_key = AppStreamKey(app_stream_entity=matched_module, name=module_name)
        cache[cache_key] = app_stream_key
        if matched_module.start_date:
            # Only include the matched if there is a start_date.
            # This adds unmatched modules to the cache (previous line)
            # but keeps it out of the response.
            app_streams.add(app_stream_key)

    return app_streams


class NEVRA(BaseModel, frozen=True):
    name: str
    epoch: str
    major: str
    minor: str
    z: str | None = None
    release: str
    arch: str

    @classmethod
    @functools.cache
    def from_string(cls, package: str) -> "NEVRA":
        """Parse a package string and return an instance of this class.

        The expected string format is name-[epoch:]version-release.architecture.

        Examples:

            cairo-1.15.12-3.el8.x86_64
            ansible-core-1:2.14.17-1.el9.x86_64
            NetworkManager-1:1.46.0-26.el9_4.x86_64
            basesystem-0:11-13.el9.noarch
            abattis-cantarell-fonts-0:0.301-4.el9.noarch

        """

        # Partition into name and version/release/architecture
        name, sep, vra = package.partition(":")
        if sep:
            name, epoch = name.rsplit("-", 1)
        else:
            # Missing epoch component. Partition on '-' instead.
            # Example: cairo-1.15.12-3.el8.x86_64
            epoch = "0"
            name, _, vra = package.partition("-")

        # Extract architecture and release
        arch_idx = vra.rindex(".")
        arch = vra[arch_idx + 1 :]

        rel_idx = vra.index("-", 0, arch_idx)
        release = vra[rel_idx + 1 : arch_idx]

        # Get the version then split in into X.Y.Z parts
        version = vra[:rel_idx]
        major, _, minor_z = version.partition(".")
        if not minor_z:
            minor = ""
            z = ""
        else:
            minor, _, z = minor_z.partition(".")

        return cls(
            name=name,
            major=major,
            minor=minor,
            z=z,
            epoch=epoch,
            release=release,
            arch=arch,
        )


@functools.cache
def app_stream_from_package(
    package: str,
    os_major: int,
) -> AppStreamKey | None:
    # FIXME: This approach to getting the stream from the package NEVRA is incorrect and flawed.
    #
    #        The package major/minor are not guaranteed to match the stream major/minor.
    #        That it matches is a coincidence, one that happens pretty often, giving the illusion
    #        the code is working as intended.
    #
    #        In order to accurately lookup the app stream from a package NEVRA string, we need to
    #        compile a list of all the versions — at least major/minor — that are in an app stream.
    #        That data does not exist today in a readily available format.
    #
    nevra = NEVRA.from_string(package)
    if app_stream_package := APP_STREAM_PACKAGES.get(os_major, {}).get(nevra.name):
        if app_stream_package.os_major == os_major:
            if app_stream_package.stream.split(".")[:2] == [nevra.major, nevra.minor]:
                return AppStreamKey(
                    app_stream_entity=app_stream_package, name=app_stream_package.application_stream_name
                )


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
    systems_by_stream: t.Annotated[dict[AppStreamKey, set[SystemInfo]], Depends(systems_by_app_stream)],
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
                    application_stream_type=app_stream.app_stream_entity.application_stream_type,
                    start_date=app_stream.app_stream_entity.start_date,
                    end_date=app_stream.app_stream_entity.end_date,
                    os_major=app_stream.app_stream_entity.os_major,
                    os_minor=app_stream.app_stream_entity.os_minor,
                    count=len(systems),
                    rolling=app_stream.app_stream_entity.rolling,
                    systems_detail=systems,
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
                        application_stream_type=app_stream.app_stream_entity.application_stream_type,
                        start_date=app_stream.app_stream_entity.start_date,
                        end_date=app_stream.app_stream_entity.end_date,
                        os_major=app_stream.app_stream_entity.os_major,
                        os_minor=app_stream.app_stream_entity.os_minor,
                        count=0,
                        rolling=app_stream.app_stream_entity.rolling,
                        systems_detail=set(),
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
