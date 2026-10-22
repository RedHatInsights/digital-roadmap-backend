import typing as t

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from roadmap.models import Meta
from roadmap.models import PaginatedSystemsResponse
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import get_relevant_app_streams
from roadmap.v1.lifecycle.app_streams import RelevantAppStreamsResponse
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream


relevant = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams", "v2"],
)


@relevant.get(
    "",
    summary="App streams based on hosts in inventory (v2 — counts only)",
    response_model=RelevantAppStreamsResponse,
)
async def get_relevant_app_streams_v2(
    systems_by_stream: t.Annotated[dict[AppStreamKey, set[SystemInfo]], Depends(systems_by_app_stream)],
    related: bool = False,
) -> RelevantAppStreamsResponse:
    """Return app stream lifecycle data with counts only (v2 thin wrapper).

    Delegates to the v1 endpoint and strips host-detail arrays from the
    response to reduce payload size.
    """
    response = await get_relevant_app_streams(systems_by_stream, related)
    return t.cast(
        RelevantAppStreamsResponse,
        {
            "meta": response["meta"],
            "data": [item.model_copy(update={"systems": set(), "systems_detail": set()}) for item in response["data"]],
        },
    )


@relevant.get(
    "/systems",
    summary="Paginated host details for a specific app stream (v2)",
    response_model=PaginatedSystemsResponse,
)
async def get_app_streams_systems_v2(
    systems_by_stream: t.Annotated[dict[AppStreamKey, set[SystemInfo]], Depends(systems_by_app_stream)],
    name: t.Annotated[str, Query(description="App stream list name or short internal name")],
    os_major: t.Annotated[int, Query(description="RHEL major version")],
    os_minor: t.Annotated[
        int | None,
        Query(
            description=(
                "Optional RHEL minor; omit to union across minors for the matched name and major. "
                "Pass it when verifying a parent-row count."
            )
        ),
    ] = None,
    offset: t.Annotated[int, Query(ge=0)] = 0,
    limit: t.Annotated[int, Query(ge=1, le=100)] = 10,
    search: str | None = None,
) -> PaginatedSystemsResponse:
    """Return paginated host details for a specific app stream.

    The name may be either the list name or the app stream entity's short name.
    When ``os_minor`` is omitted, the result is the union of all matching
    name-and-major keys, so ``meta.total`` may exceed a single parent list
    row's ``count``. Callers verifying a parent row's count must pass that
    row's ``os_minor`` (omitting it only when the row's minor is null).

    When ``os_minor`` is supplied, an exact minor match takes precedence over
    an entity with no minor, which acts as a wildcard. Results are then sorted,
    filtered by optional display-name search, and paginated in Python.
    """
    query_name = name.casefold()
    exact_systems: set[SystemInfo] | None = None
    wildcard_systems: set[SystemInfo] = set()
    union_systems: set[SystemInfo] = set()

    # Late #431 / CodeRabbit requested deterministic matching: only an entity
    # with os_minor=None could wildcard, and omitting os_minor with no such
    # entity returned empty. That re-broke RHEL 9 package streams with
    # os_minor=0, docs/support calls that omit the minor, and short names that
    # differ from list names such as "Redis 6". RHINENG-32627 intentionally
    # reverses that omit->empty rule: omission means union by name+major, and
    # matching accepts the entity's short name. Do not re-adopt the
    # deterministic omit path without revisiting this ticket.
    for key, systems in systems_by_stream.items():
        if key.name.casefold() != query_name and key.app_stream_entity.name.casefold() != query_name:
            continue
        if key.app_stream_entity.os_major != os_major:
            continue

        entity_minor = key.app_stream_entity.os_minor
        if os_minor is None:
            union_systems.update(systems)
            continue
        if entity_minor == os_minor:
            exact_systems = systems
            break
        if entity_minor is None:
            wildcard_systems.update(systems)

    if os_minor is None:
        matching_systems = union_systems
    elif exact_systems is not None:
        matching_systems = exact_systems
    else:
        matching_systems = wildcard_systems

    filtered = sorted(matching_systems, key=lambda s: (s.display_name, str(s.id)))

    if search:
        search_lower = search.lower()
        filtered = [s for s in filtered if search_lower in s.display_name.lower()]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return PaginatedSystemsResponse(
        meta=Meta(count=len(page), total=total),
        data=page,
    )
