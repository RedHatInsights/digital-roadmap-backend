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
from roadmap.v1.upcoming import get_upcoming_data_with_hosts
from roadmap.v1.upcoming import get_upcoming_relevant
from roadmap.v1.upcoming import packages_by_system
from roadmap.v1.upcoming import WrappedUpcomingOutput


router = APIRouter(
    prefix="/relevant/upcoming-changes",
    tags=["Relevant", "Upcoming Changes"],
)


@router.post(
    "/hosts",
    summary="Upcoming changes for a specified list of hosts",
    response_model=WrappedUpcomingOutput,
)
async def get_relevant_upcoming_for_hosts(
    body: HostIdsRequest,
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    all: bool = False,
):
    """Return upcoming changes for the given hosts.

    Same payload as the v1 relevant upcoming changes endpoint. The inventory
    query is limited to these ids and to the groups this caller may read. Ids
    the caller cannot read are omitted. The query reads installed packages,
    because a host matches an item only when its RHEL major equals the item's
    major and its package names intersect the item's package set.

    With all=false, only items that match at least one host in this request
    are returned. An item that matches only a host left out of the request is
    absent. With all=true, every known item is returned, and affected systems
    are still only hosts from this request. To match one request for all
    accessible hosts when processing batches, merge rows that share a name and
    release, union the affected systems, and count each host once. Drop a row
    that has no affected systems when all=false, then recalculate metadata.
    Concatenating responses is not enough. Item names stay the same across
    batches because they come from the upcoming file.
    """
    systems = await query_host_inventory_by_ids(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        host_ids=body.host_ids,
        include_packages=True,
    )
    try:
        packages = await packages_by_system(org_id, systems)
    except (DBAPIError, SQLAlchemyError):
        log_database_error("Database error querying host inventory")
        raise HTTPException(
            status_code=500,
            detail="Error querying host inventory",
        ) from None

    data = get_upcoming_data_with_hosts(packages, settings, all)
    return await get_upcoming_relevant(data, all)
