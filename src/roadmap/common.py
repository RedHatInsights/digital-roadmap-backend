import base64
import gzip
import json
import logging
import typing as t
import urllib.parse
import urllib.request

from datetime import date
from pathlib import Path
from urllib.error import HTTPError

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from roadmap.config import SETTINGS
from roadmap.models import LifecycleType


logger = logging.getLogger("uvicorn.error")


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/v1/ping") == -1


async def query_rbac(
    x_rh_identity: str | None,
) -> list[dict[t.Any, t.Any]]:
    if SETTINGS.dev:
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    params = {
        "application": "inventory",
        "limit": 1000,
    }

    headers = {"X-RH-Identity": x_rh_identity} if x_rh_identity else {}
    req = urllib.request.Request(
        f"{SETTINGS.rbac_url}/api/rbac/v1/access/?{urllib.parse.urlencode(params, doseq=True)}",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        logger.error(f"Problem querying RBAC: {err}")
        raise HTTPException(status_code=err.code, detail=err.msg)

    return data.get("data", [])


async def check_inventory_access(permissions: list[dict[t.Any, t.Any]]) -> tuple[bool, list[str]]:
    """Check the given permissions for inventory access.

    Return a boolean as well as any detailed access definitions.
    """
    inventory_access_perms = {"inventory:*:*", "inventory:hosts:read"}

    has_access = False
    resource_definitions = []
    for permission in permissions:
        if perm := permission["resourceDefinitions"]:
            resource_definitions.append(*perm)
        else:
            if permission["permission"] in inventory_access_perms:
                has_access = True

    return has_access, resource_definitions


# FIXME: This should be cached
async def query_host_inventory(
    session: AsyncSession,
    org_id: str,
    groups: list[str] | None = None,
    major: int | None = None,
    minor: int | None = None,
):
    if SETTINGS.dev:
        if not org_id:
            org_id = "test"

        logger.debug("Running in development mode. Returning fixture response data for inventory.")
        file = Path(__file__).resolve()
        response_data_file = file.parent.parent.parent / "tests" / "fixtures" / "inventory_db_response.json.gz"
        with gzip.open(response_data_file) as gzfile:
            response_data = json.load(gzfile)

        if major is not None:
            response_data = [
                item
                for item in response_data
                if item.get("system_profile_facts", {}).get("operating_system", {}).get("major") == major
            ]

        if minor is not None:
            response_data = [
                item
                for item in response_data
                if item.get("system_profile_facts", {}).get("operating_system", {}).get("minor") == minor
            ]

        for item in response_data:
            yield item

        return

    if groups:
        # TODO: Implement group filtering
        raise HTTPException(501, detail="Group filtering is not yet implemented")

    query = "SELECT * FROM hbi.hosts WHERE org_id = :org_id"
    if major is not None:
        query = f"{query} AND system_profile_facts #>> '{{operating_system,major}}' = :major"

    if minor is not None:
        query = f"{query} AND system_profile_facts #>> '{{operating_system,minor}}' = :minor"

    result = await session.stream(
        text(query),
        params={
            "org_id": org_id,
            "major": str(major),
            "minor": str(minor),
        },
    )
    async for row in result.mappings():
        yield row


def get_lifecycle_type(products: list[dict[str, str]]) -> LifecycleType:
    """Calculate lifecycle type based on the product ID.

    https://downloads.corp.redhat.com/internal/products
    https://github.com/RedHatInsights/rhsm-subscriptions/tree/main/swatch-product-configuration/src/main/resources/subscription_configs/RHEL

    Mainline < EUS < E4S/EEUS

    EUS --> 70, 73, 75
    ELS --> 204
    E4S/EEUS --> 241

    """
    ids = {item.get("id") for item in products}
    type = LifecycleType.mainline

    if any(id in ids for id in {"70", "73", "75"}):
        type = LifecycleType.eus

    if "204" in ids:
        type = LifecycleType.els

    if "241" in ids:
        type = LifecycleType.e4s

    return type


def sort_attrs(attr, /, *attrs) -> t.Callable:
    def _getter(item):
        # If an attribute is None, use a 0 instead of None for the purpose of sorting
        # FIXME: There is a bug if getatter() is an empty string "", a 0 is used instead of an empty string.
        return tuple(getattr(item, a) or 0 for a in (attr, *attrs))

    return _getter


def ensure_date(value: str | date):
    """Ensure the date value is a date object."""
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Date must be in ISO 8601 format")


def decode_header(encoded_header: str | None) -> str:
    # https://github.com/RedHatInsights/identity-schemas/blob/main/3scale/identities/basic.json
    if encoded_header is None:
        return ""

    decoded_id_header = base64.b64decode(encoded_header).decode("utf-8")
    id_header = json.loads(decoded_id_header)
    identity = id_header.get("identity", {})
    org_id = identity.get("org_id", "")

    return org_id
