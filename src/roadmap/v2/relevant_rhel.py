import typing as t

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import query_host_inventory
from roadmap.common import query_rhel_systems
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import LifecycleType
from roadmap.models import PaginatedSystemsResponse
from roadmap.v1.lifecycle.rhel import get_relevant_systems
from roadmap.v1.lifecycle.rhel import RelevantSystemsResponse


MajorVersion = t.Annotated[int, Path(description="Major version number", ge=7, le=10)]
MinorVersion = t.Annotated[int, Path(description="Minor version number", ge=0, le=10)]

relevant = APIRouter(
    prefix="/relevant/lifecycle/rhel",
    tags=["Relevant", "RHEL", "v2"],
)


@relevant.get(
    "",
    summary="RHEL lifecycle dates for systems in inventory (v2 — counts only)",
    response_model=RelevantSystemsResponse,
)
async def get_relevant_systems_v2(
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[t.Any, Depends(query_host_inventory)],
    related: bool = False,
) -> RelevantSystemsResponse:
    response = await get_relevant_systems(org_id, systems, related)
    for item in response.data:
        item.systems_detail = set()
        item.systems = set()
    return response


@relevant.get(
    "/{major}/{minor}/systems",
    summary="Paginated host details for a specific RHEL version (v2)",
    response_model=PaginatedSystemsResponse,
)
async def get_rhel_systems_v2(
    major: MajorVersion,
    minor: MinorVersion,
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    lifecycle_type: LifecycleType = LifecycleType.mainline,
    offset: t.Annotated[int, Query(ge=0)] = 0,
    limit: t.Annotated[int, Query(ge=1, le=100)] = 10,
    search: str | None = None,
) -> PaginatedSystemsResponse:
    return await query_rhel_systems(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        major=major,
        minor=minor,
        lifecycle_type=lifecycle_type,
        offset=offset,
        limit=limit,
        search=search,
    )
