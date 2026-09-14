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
    for item in response["data"]:
        item.systems_detail = set()
        item.systems = set()
    return t.cast(RelevantAppStreamsResponse, response)


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
) -> PaginatedSystemsResponse:
    """Return paginated host details for a specific app stream.

    Matches hosts by stream name and OS version from the pre-computed
    systems-by-stream mapping, then applies Python-level pagination and
    optional display-name search.
    """
    matching_systems: set[SystemInfo] = set()
    for key, systems in systems_by_stream.items():
        if (
            key.name == name
            and key.app_stream_entity.os_major == os_major
            and key.app_stream_entity.os_minor == os_minor
        ):
            matching_systems = systems
            break

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
