import typing as t

from collections import Counter

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import query_filtered_host_inventory
from roadmap.common import query_host_inventory
from roadmap.common import rhel_major_minor
from roadmap.config import Settings
from roadmap.data import app_stream_inventory_candidates
from roadmap.data import APP_STREAM_MODULES_BY_KEY
from roadmap.data import MODULE_PACKAGES
from roadmap.data import OS_MAJORS_BY_APP_NAME
from roadmap.data import SHARED_PACKAGE_NAMES_BY_OS_MAJOR
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.database import get_db
from roadmap.models import Meta
from roadmap.models import PaginatedSystemsResponse
from roadmap.models import SortOrder
from roadmap.models import SupportStatus
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import app_stream_from_package
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import ModuleStatus
from roadmap.v1.lifecycle.app_streams import NEVRA
from roadmap.v1.lifecycle.app_streams import related_app_streams
from roadmap.v1.lifecycle.app_streams import RelevantAppStream
from roadmap.v1.lifecycle.app_streams import RelevantAppStreamsResponse


relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams", "v2"],
)


def _candidate_names(name: str | None, os_major: int | None) -> tuple[set[str], set[str]]:
    """Return conservative HBI filters for the requested App Stream.

    The canonical inventory metadata lives with the App Stream definitions.
    These names only reduce the rows read from HBI.  `_host_matches` remains the
    source of truth for the complete module/package matching semantics.
    """
    return app_stream_inventory_candidates(name, os_major)


async def _query_v2_app_stream_inventory(
    *,
    org_id: str,
    session: AsyncSession,
    settings: Settings,
    host_groups: set[str | None],
    name: str | None,
    os_major: int | None,
) -> t.AsyncGenerator[t.Any, None]:
    module_names, package_names = _candidate_names(name, os_major)
    async for result in query_filtered_host_inventory(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        major=os_major,
        # App Stream os_minor is lifecycle metadata, not the host profile
        # minor.  Keep the old route semantics and resolve it in _host_matches.
        minor=None,
        module_names=module_names,
        package_names=package_names,
    ):
        yield result


async def query_v2_all_app_stream_inventory(
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
):
    """Read all inventory rows for the App Stream list.

    The list query needs every host so that its result can be compared directly
    with the unfiltered V1 calculation.  Candidate filtering is still used by
    the on-demand systems endpoint, where the requested App Stream and RHEL
    major provide a much narrower candidate set.
    """
    async for result in query_host_inventory(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
    ):
        yield result


async def query_v2_target_app_stream_inventory(
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    name: str,
    os_major: int,
) -> t.AsyncGenerator[t.Any, None]:
    """Read candidate-filtered inventory rows for one App Stream."""
    async for result in _query_v2_app_stream_inventory(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        name=name,
        os_major=os_major,
    ):
        yield result


def _module_matches(modules, os_major, module_cache, pending):
    matches = set()
    for module in modules:
        module_name = module["name"]
        stream = module["stream"]
        if "perl" in module_name.casefold() or os_major not in OS_MAJORS_BY_APP_NAME.get(module_name, []):
            continue
        status = set(module.get("status", []))
        included = {ModuleStatus.enabled, ModuleStatus.installed}
        if (os_major <= 8 and not status.intersection(included)) or (
            os_major > 8 and status and not status.intersection(included)
        ):
            continue

        cache_key = (module_name, os_major, stream)
        if ModuleStatus.enabled in status:
            expected = MODULE_PACKAGES.get(cache_key)
            entity = APP_STREAM_MODULES_BY_KEY.get(cache_key)
            if expected and entity and entity.start_date:
                pending[cache_key] = (AppStreamKey(name=module_name, app_stream_entity=entity), expected)
            continue

        cached = module_cache.get(cache_key)
        if cached:
            if cached.app_stream_entity.start_date:
                matches.add(cached)
            continue

        entity = APP_STREAM_MODULES_BY_KEY.get(cache_key)
        if not entity:
            entity = AppStreamEntity(
                name=module_name,
                stream=stream,
                start_date=None,
                end_date=None,
                application_stream_name=SupportStatus.unknown,
                impl=AppStreamImplementation.module,
            )
        app_stream = AppStreamKey(name=module_name, app_stream_entity=entity)
        module_cache[cache_key] = app_stream
        if entity.start_date:
            matches.add(app_stream)
    return matches


def _host_matches(system, module_cache):
    try:
        os_major, os_minor = rhel_major_minor(system)
    except ValueError:
        return None

    packages = system["packages"] or []
    installed_names = {NEVRA.from_string(package).name for package in packages}
    pending = {}
    matches = _module_matches(system["dnf_modules"] or [], os_major, module_cache, pending)

    for cache_key, (app_stream, expected) in pending.items():
        matched = expected & installed_names
        shared = SHARED_PACKAGE_NAMES_BY_OS_MAJOR.get(os_major, set())
        if matched and ((matched - shared) or cache_key[0] in installed_names):
            matches.add(app_stream)

    for package in packages:
        if app_stream := app_stream_from_package(package, os_major):
            matches.add(app_stream)
    return os_major, os_minor, matches


def _response_item(key, count):
    entity = key.app_stream_entity
    return RelevantAppStream(
        name=key.name,
        display_name=entity.display_name,
        application_stream_name=entity.application_stream_name,
        application_stream_type=entity.application_stream_type,
        start_date=entity.start_date,
        end_date=entity.end_date,
        os_major=entity.os_major,
        os_minor=entity.os_minor,
        count=count,
        rolling=entity.rolling,
        systems=set(),
        systems_detail=set(),
        related=count == 0,
    )


async def _count_app_streams(systems, related):
    counts = Counter()
    module_cache = {}
    async for system in systems.yield_per(2_000).mappings():
        result = _host_matches(system, module_cache)
        if result is None:
            continue
        for key in result[2]:
            counts[key] += 1

    keys = list(counts)
    if related:
        related_keys = related_app_streams(keys)
        keys.extend(sorted(related_keys - set(keys), key=lambda key: (key.name, str(key.app_stream_entity.os_major))))
    data = [_response_item(key, counts.get(key, 0)) for key in keys if not key.app_stream_entity.rolling]
    return RelevantAppStreamsResponse(meta=Meta(count=len(data), total=len(data)), data=data)


@relevant.get(
    "",
    summary="App streams based on hosts in inventory (v2 — counts only)",
    response_model=RelevantAppStreamsResponse,
)
async def get_relevant_app_streams_v2(
    systems: t.Annotated[t.Any, Depends(query_v2_all_app_stream_inventory)],
    related: bool = False,
) -> RelevantAppStreamsResponse:
    """Count matching AppStreams without retaining a host-to-stream mapping."""
    return await _count_app_streams(systems, related)


@relevant.get(
    "/systems",
    summary="Paginated host details for a specific app stream (v2)",
    response_model=PaginatedSystemsResponse,
)
async def get_app_streams_systems_v2(
    systems: t.Annotated[t.Any, Depends(query_v2_target_app_stream_inventory)],
    name: t.Annotated[str, Query(description="App stream internal name")],
    os_major: t.Annotated[int, Query(description="RHEL major version")],
    os_minor: t.Annotated[int | None, Query(description="RHEL minor version")] = None,
    offset: t.Annotated[int, Query(ge=0)] = 0,
    limit: t.Annotated[int, Query(ge=1, le=100)] = 10,
    search: str | None = None,
    sort_order: SortOrder = SortOrder.asc,
) -> PaginatedSystemsResponse:
    """Find and paginate matching hosts without materializing all streams."""
    exact = []
    wildcard = []
    module_cache = {}
    async for system in systems.yield_per(2_000).mappings():
        result = _host_matches(system, module_cache)
        if result is None or result[0] != os_major:
            continue
        info = SystemInfo(id=system["id"], display_name=system["display_name"], os_major=result[0], os_minor=result[1])
        exact_match = False
        wildcard_match = False
        for key in result[2]:
            entity = key.app_stream_entity
            if key.name != name or entity.os_major != os_major:
                continue
            if entity.os_minor is None:
                wildcard_match = True
            elif os_minor is not None and entity.os_minor == os_minor:
                exact_match = True
        if exact_match:
            exact.append(info)
        elif wildcard_match:
            wildcard.append(info)

    matching = exact if exact else wildcard
    if search:
        search_lower = search.lower()
        matching = [item for item in matching if search_lower in item.display_name.lower()]
    matching.sort(key=lambda item: (item.display_name, str(item.id)), reverse=sort_order == SortOrder.desc)
    page = matching[offset : offset + limit]
    return PaginatedSystemsResponse(meta=Meta(count=len(page), total=len(matching)), data=page)
