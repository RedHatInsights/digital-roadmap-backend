import logging
import typing as t

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncResult

from roadmap.common import decode_header
from roadmap.common import query_accessible_host_uuids


logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/lifecycle",
    tags=["Lifecycle", "v2"],
)


class AccessibleHostUuidsResponse(BaseModel):
    """Host UUIDs the caller is permitted to read from host inventory."""

    accessible_host_uuids: list[UUID]


@router.get(
    "/host_uuids",
    summary="Host UUIDs the caller is permitted to read",
    response_model=AccessibleHostUuidsResponse,
)
async def get_accessible_host_uuids(
    org_id: t.Annotated[str, Depends(decode_header)],
    hosts: t.Annotated[AsyncResult[t.Any], Depends(query_accessible_host_uuids)],
) -> AccessibleHostUuidsResponse:
    """Return every host UUID this user can access.

    Authorization happens in the inventory dependency: RBAC or Kessel decides
    which host groups are visible, and dev mode skips that remote check.
    The query itself only reads host ids.
    """
    logger.info(f"Listing accessible host UUIDs for {org_id or 'UNKNOWN'}")

    # The stream yields one row per host, and each row is just the id.
    uuids = [row["id"] async for row in hosts.mappings()]
    return AccessibleHostUuidsResponse(accessible_host_uuids=uuids)
