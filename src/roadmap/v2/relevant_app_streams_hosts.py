import typing as t

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import query_host_inventory_by_ids
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.v1.lifecycle.app_streams import get_relevant_app_streams
from roadmap.v1.lifecycle.app_streams import RelevantAppStreamsResponse
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream


class HostIdsRequest(BaseModel):
    """Host ids to read. The caller must also be permitted to see them."""

    host_ids: list[UUID] = Field(min_length=1, max_length=10_000)


router = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams", "v2"],
)


async def _relevant_for_hosts(org_id: str, systems: AsyncResult, related: bool):
    """Return the v1 relevant-app-streams payload for these inventory rows.

    Switching this endpoint to the v2 counts implementation is a local change:
    call system_counts_by_app_stream and get_relevant_app_streams_v2, and set
    the route response_model to RelevantAppStreamsResponseV2. The inventory
    query stays the same.
    """
    systems_by_stream = await systems_by_app_stream(org_id, systems)
    return await get_relevant_app_streams(systems_by_stream, related)


@router.post(
    "/hosts",
    summary="App streams for a specified list of hosts",
    response_model=RelevantAppStreamsResponse,
)
async def get_relevant_app_streams_for_hosts(
    body: HostIdsRequest,
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    related: bool = False,
):
    """Return app streams for the given hosts.

    Same payload as the v1 relevant app streams endpoint. The inventory query
    is limited to these ids and to the groups this caller may read. Ids the
    caller cannot read are omitted.
    """
    systems = await query_host_inventory_by_ids(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        host_ids=body.host_ids,
    )
    return await _relevant_for_hosts(org_id, systems, related)
