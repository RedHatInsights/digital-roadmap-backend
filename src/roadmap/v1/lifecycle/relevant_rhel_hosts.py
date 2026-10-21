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
from roadmap.v1.lifecycle.rhel import relevant_systems
from roadmap.v1.lifecycle.rhel import RelevantSystemsResponse


router = APIRouter(
    prefix="/relevant/lifecycle/rhel",
    tags=["Relevant", "RHEL"],
)


@router.post(
    "/hosts",
    summary="RHEL lifecycle dates for a specified list of hosts",
    response_model=RelevantSystemsResponse,
)
async def get_relevant_rhel_for_hosts(
    body: HostIdsRequest,
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    related: bool = False,
):
    """Return RHEL lifecycle data for the given hosts.

    Same payload as the v1 relevant RHEL endpoint. The inventory query is
    limited to these ids and to the groups this caller may read. Ids the
    caller cannot read are omitted. The query reads host IDs, display names,
    OS fields (including os_release), and installed products, but not packages
    or DNF modules.

    With related=true, related versions are calculated for the hosts in this
    request. A version returned as related may be installed on a host left out
    of the request; including that host leaves the version out of the related
    set and returns it on that host's installed lifecycle row. Each related
    row comes from one lifecycle record for that version and always uses
    lifecycle type mainline, so its identity stays the same across batches.
    Installed lifecycle types stay on their own rows. To match a request for
    all accessible hosts when processing batches, merge installed rows that
    share an OS name, version, and lifecycle type, counting each host once.
    Drop a related version when any batch has that version installed, then
    recalculate metadata. Concatenating responses is not enough.
    """
    systems = await query_host_inventory_by_ids(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        host_ids=body.host_ids,
        include_packages=False,
    )
    try:
        return await relevant_systems(org_id, systems, related)
    except (DBAPIError, SQLAlchemyError):
        log_database_error("Database error querying host inventory")
        raise HTTPException(
            status_code=500,
            detail="Error querying host inventory",
        ) from None
