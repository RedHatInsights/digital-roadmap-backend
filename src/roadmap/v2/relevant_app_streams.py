import logging
import typing as t

from collections import Counter
from collections import defaultdict
from datetime import date

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import model_validator
from sqlalchemy.ext.asyncio import AsyncResult

from roadmap.common import decode_header
from roadmap.common import query_host_inventory
from roadmap.common import rhel_major_minor
from roadmap.common import sort_attrs
from roadmap.data.app_streams import AppStreamType
from roadmap.models import _calculate_support_status
from roadmap.models import Meta
from roadmap.models import PaginatedSystemsResponse
from roadmap.models import SortOrder
from roadmap.models import SupportStatus
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import app_stream_from_package
from roadmap.v1.lifecycle.app_streams import app_streams_from_modules
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import NEVRA
from roadmap.v1.lifecycle.app_streams import related_app_streams
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream
from roadmap.v1.lifecycle.app_streams import verified_app_streams_from_modules


logger = logging.getLogger("uvicorn.error")


class RelevantAppStreamV2(BaseModel):
    """App stream lifecycle information with a system count and no host details."""

    name: str
    application_stream_name: str
    application_stream_type: AppStreamType | None = None
    display_name: str
    os_major: int | None
    os_minor: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    count: int
    rolling: bool = False
    support_status: SupportStatus = SupportStatus.unknown
    related: bool = False

    @model_validator(mode="after")
    def update_support_status(self):
        if self.count == 0:
            self.support_status = SupportStatus.not_installed
        else:
            self.support_status = _calculate_support_status(
                start_date=self.start_date,
                end_date=self.end_date,
                current_date=date.today(),
                months=6,
            )
        return self


class RelevantAppStreamsResponseV2(BaseModel):
    meta: Meta
    data: list[RelevantAppStreamV2]


async def system_counts_by_app_stream(
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[AsyncResult, Depends(query_host_inventory)],
) -> dict[AppStreamKey, int]:
    """Count streams once per inventory host, without retaining host information.

    Inventory yields one row per host. Only stream counts and matching caches
    survive between rows; module and package matches are deduplicated per host.
    """
    logger.info(f"Getting relevant app stream counts for {org_id or 'UNKNOWN'}")

    missing = defaultdict(int)
    counts: Counter[AppStreamKey] = Counter()
    module_cache = {}
    module_keys: dict[AppStreamKey, None] = {}
    package_keys: dict[AppStreamKey, None] = {}
    async for system in systems.yield_per(2_000).mappings():
        dnf_modules = system["dnf_modules"] or []
        packages = system["packages"] or []

        try:
            os_major, _os_minor = rhel_major_minor(system)
        except ValueError:
            missing["os_version"] += 1
            continue

        if not dnf_modules:
            missing["dnf_modules"] += 1

        if not packages:
            missing["packages"] += 1

        # Names are parsed only when an enabled module needs package verification.
        modules_pending_verification = {}
        module_app_streams = app_streams_from_modules(dnf_modules, os_major, module_cache, modules_pending_verification)
        for app_stream in module_app_streams:
            module_keys.setdefault(app_stream)

        if modules_pending_verification:
            installed_package_names = {NEVRA.from_string(pkg).name for pkg in packages}
            for app_stream in verified_app_streams_from_modules(modules_pending_verification, installed_package_names):
                module_keys.setdefault(app_stream)
                module_app_streams.add(app_stream)

        for package in packages:
            if app_stream := app_stream_from_package(package, os_major):
                package_keys.setdefault(app_stream)
                module_app_streams.add(app_stream)

        counts.update(module_app_streams)

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    # v1 processes all modules before packages, in first-seen package order.
    # Keep that order and the original keys: related streams inherit their names.
    result = {app_stream: counts[app_stream] for app_stream in module_keys}
    result.update({app_stream: counts[app_stream] for app_stream in package_keys})
    return result


relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams", "v2"],
)


@relevant.get(
    "",
    summary="App streams based on hosts in inventory (v2 — counts only)",
    response_model=RelevantAppStreamsResponseV2,
)
async def get_relevant_app_streams_v2(
    system_counts: t.Annotated[dict[AppStreamKey, int], Depends(system_counts_by_app_stream)],
    related: bool = False,
) -> RelevantAppStreamsResponseV2:
    """Return app stream lifecycle data and counts of systems using each stream."""
    counts = system_counts.copy()
    if related:
        counts.update(dict.fromkeys(related_app_streams(system_counts), 0))

    relevant_app_streams = []
    for app_stream, count in counts.items():
        entity = app_stream.app_stream_entity
        if entity.rolling:
            continue

        try:
            relevant_app_streams.append(
                RelevantAppStreamV2(
                    name=app_stream.name,
                    display_name=entity.display_name,
                    application_stream_name=entity.application_stream_name,
                    application_stream_type=entity.application_stream_type,
                    start_date=entity.start_date,  # pyright: ignore [reportArgumentType]
                    end_date=entity.end_date,  # pyright: ignore [reportArgumentType]
                    os_major=entity.os_major,
                    os_minor=entity.os_minor,
                    count=count,
                    rolling=entity.rolling,
                    related=count == 0,
                )
            )
        except Exception as exc:
            raise HTTPException(detail=str(exc), status_code=400)

    return RelevantAppStreamsResponseV2(
        meta=Meta(count=len(relevant_app_streams), total=sum(item.count for item in relevant_app_streams)),
        data=sorted(relevant_app_streams, key=sort_attrs("name", "os_major", "os_minor")),
    )


@relevant.get(
    "/systems",
    summary="Paginated host details for a specific app stream (v2)",
    response_model=PaginatedSystemsResponse,
)
async def get_app_streams_systems_v2(
    systems_by_stream: t.Annotated[dict[AppStreamKey, set[SystemInfo]], Depends(systems_by_app_stream)],
    name: t.Annotated[str, Query(description="App stream internal name")],
    os_major: t.Annotated[int, Query(description="RHEL major version")],
    os_minor: t.Annotated[int | None, Query(description="RHEL minor version")] = None,
    offset: t.Annotated[int, Query(ge=0)] = 0,
    limit: t.Annotated[int, Query(ge=1, le=100)] = 10,
    search: str | None = None,
    sort_order: SortOrder = SortOrder.asc,
) -> PaginatedSystemsResponse:
    """Return paginated host details for a specific app stream.

    Matches hosts by stream name and OS version from the pre-computed
    systems-by-stream mapping, then applies Python-level pagination and
    optional display-name search.
    """
    matching_systems: set[SystemInfo] = set()
    wildcard_systems: set[SystemInfo] = set()
    for key, systems in systems_by_stream.items():
        if key.name != name or key.app_stream_entity.os_major != os_major:
            continue
        entity_minor = key.app_stream_entity.os_minor
        if entity_minor is not None and os_minor is not None and entity_minor == os_minor:
            matching_systems = systems
            break
        if entity_minor is None:
            wildcard_systems = systems
    if not matching_systems:
        matching_systems = wildcard_systems

    filtered = sorted(
        matching_systems,
        key=lambda s: (s.display_name, str(s.id)),
        reverse=(sort_order == SortOrder.desc),
    )

    if search:
        search_lower = search.lower()
        filtered = [s for s in filtered if search_lower in s.display_name.lower()]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return PaginatedSystemsResponse(
        meta=Meta(count=len(page), total=total),
        data=page,
    )
