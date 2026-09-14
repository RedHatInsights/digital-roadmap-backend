import typing as t

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from roadmap.config import Settings
from roadmap.models import Meta
from roadmap.models import PaginatedSystemsResponse
from roadmap.models import SystemInfo
from roadmap.v1.upcoming import get_upcoming_data_with_hosts
from roadmap.v1.upcoming import get_upcoming_relevant
from roadmap.v1.upcoming import packages_by_system
from roadmap.v1.upcoming import read_upcoming_file
from roadmap.v1.upcoming import WrappedUpcomingOutput


relevant = APIRouter(
    prefix="/relevant/upcoming-changes",
    tags=["Relevant", "Upcoming Changes", "v2"],
)


@relevant.get(
    "",
    summary="Upcoming changes relevant to systems in inventory (v2 — counts only)",
    response_model=WrappedUpcomingOutput,
)
async def get_upcoming_relevant_v2(
    data: t.Annotated[t.Any, Depends(get_upcoming_data_with_hosts)],
    all: bool = False,
):
    response = await get_upcoming_relevant(data, all)
    for item in response["data"]:
        item.details.potentiallyAffectedSystemsDetail = set()
        item.details.potentiallyAffectedSystems = set()
    return response


@relevant.get(
    "/systems",
    summary="Paginated host details for a specific upcoming change (v2)",
    response_model=PaginatedSystemsResponse,
)
async def get_upcoming_systems_v2(
    pkg_by_system: t.Annotated[dict[SystemInfo, set[str]], Depends(packages_by_system)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    name: t.Annotated[str, Query(description="Upcoming change name")],
    release: t.Annotated[str, Query(description="Release version string")],
    offset: t.Annotated[int, Query(ge=0)] = 0,
    limit: t.Annotated[int, Query(ge=1, le=100)] = 10,
    search: str | None = None,
) -> PaginatedSystemsResponse:
    upcoming_items = read_upcoming_file(settings.upcoming_json_path)

    target = None
    for item in upcoming_items:
        if item.name == name and item.release == release:
            target = item
            break

    if target is None:
        return PaginatedSystemsResponse(
            meta=Meta(count=0, total=0),
            data=[],
        )

    matching_systems: set[SystemInfo] = set()
    for system, packages in pkg_by_system.items():
        if system.os_major == target.os_major:
            if target.packages.intersection(packages):
                matching_systems.add(system)

    filtered = sorted(matching_systems, key=lambda s: s.display_name)

    if search:
        search_lower = search.lower()
        filtered = [s for s in filtered if search_lower in s.display_name.lower()]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return PaginatedSystemsResponse(
        meta=Meta(count=len(page), total=total),
        data=page,
    )
