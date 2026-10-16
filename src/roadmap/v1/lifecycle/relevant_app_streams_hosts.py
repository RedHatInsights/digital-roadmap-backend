import typing as t

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import log_database_error
from roadmap.common import query_host_inventory_by_ids
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import HostIdsRequest
from roadmap.v1.lifecycle.app_streams import build_relevant_app_streams
from roadmap.v1.lifecycle.app_streams import RelevantAppStreamsResponse
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream


router = APIRouter(
    prefix="/relevant/lifecycle/app-streams",
    tags=["Relevant", "App Streams"],
)


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

    With related=true, related streams are calculated for the hosts in this
    request. A stream returned as related may be installed on a host left out
    of the request; including that host can return it as installed instead.
    A related row takes its name from the installed stream that produced it,
    so the same related stream can have a different name in another batch.
    When processing batches, merge installed rows, counting each host once,
    and collect related rows by stream identity. Drop a related row if that
    stream is installed in any batch, then recalculate metadata. Related row
    names may still differ from a single request for all accessible hosts.
    Concatenating responses is not enough.
    """
    systems = await query_host_inventory_by_ids(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        host_ids=body.host_ids,
    )
    try:
        systems_by_stream = await systems_by_app_stream(org_id, systems)
    except (DBAPIError, SQLAlchemyError):
        log_database_error("Database error querying host inventory")
        raise HTTPException(
            status_code=500,
            detail="Error querying host inventory",
        ) from None

    return build_relevant_app_streams(systems_by_stream, related)
