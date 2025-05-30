import base64
import json
import logging
import textwrap
import typing as t
import urllib.parse
import urllib.request

from datetime import date
from urllib.error import HTTPError
from uuid import UUID

from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import LifecycleType


logger = logging.getLogger("uvicorn.error")

MajorVersion = t.Annotated[int | None, Query(description="Major version number", ge=8, le=10)]
MinorVersion = t.Annotated[int | None, Query(description="Minor version number", ge=0, le=10)]


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        filters = (
            "/v1/ping",
            "/metrics",
        )
        return not any(filter in message for filter in filters)


async def decode_header(
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
) -> str:
    # https://github.com/RedHatInsights/identity-schemas/blob/main/3scale/identities/basic.json
    if x_rh_identity is None:
        return ""

    decoded_id_header = base64.b64decode(x_rh_identity).decode("utf-8")
    id_header = json.loads(decoded_id_header)
    identity = id_header.get("identity", {})
    org_id = identity.get("org_id", "")

    return org_id


async def query_rbac(
    settings: t.Annotated[Settings, Depends(Settings.create)],
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
) -> list[dict[t.Any, t.Any]]:
    if settings.dev:
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
    if not settings.rbac_url:
        return [{}]

    req = urllib.request.Request(
        f"{settings.rbac_url}/api/rbac/v1/access/?{urllib.parse.urlencode(params, doseq=True)}",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        logger.error(f"Problem querying RBAC: {err}")
        raise HTTPException(status_code=err.code, detail=err.msg)

    return data.get("data", [{}])


def _get_group_list_from_resource_definition(resource_definition: dict) -> list[str]:
    if attributeFilter := resource_definition.get("attributeFilter"):
        if attributeFilter.get("key") != "group.id":
            raise HTTPException(501, detail="Invalid value for attributeFilter.key in RBAC response.")
        op = attributeFilter.get("operation")
        if op not in ("in", "equal"):
            raise HTTPException(501, detail="Invalid value for attributeFilter.operation in RBAC response.")
        val = attributeFilter.get("value")
        if op == "in":
            if not isinstance(val, list):
                raise HTTPException(501, detail="Did not receive a list for attributeFilter.value in RBAC response.")
        else:
            if not isinstance(val, str):
                raise HTTPException(501, detail="Did not receive a str for attributeFilter.value in RBAC response.")
            val = [val]

        group_list = val
        # Validate that all values in the filter are UUIDs.
        for gid in group_list:
            # It is possible that the group id is None, which means
            # permission to access a host who belongs to a group which
            # has its "ungrouped" attribute set to True.
            # TODO: Check if this None check can be removed once the Kessel Phase 0 migration is complete.
            # https://issues.redhat.com/browse/RHINENG-16842
            if gid is not None:
                try:
                    UUID(gid)
                except (ValueError, TypeError):
                    logger.warning(f"RBAC attributeFilter contained erroneous UUID: '{gid}'")
                    raise HTTPException(
                        501, detail="Received invalid UUIDs for attributeFilter.value in RBAC response."
                    )
        return group_list
    raise HTTPException(501, detail="RBAC resourceDefinition had no attributeFilter.")


async def get_allowed_host_groups(
    permissions: t.Annotated[list[dict[t.Any, t.Any]], Depends(query_rbac)],
) -> set[str | None]:
    """Check the given permissions for inventory access.

    Raise HTTPException if no permissions allow access.

    Return set of groups hosts may belong to, if restricted, otherwise returns
    an empty set, meaning unrestricted access to the org's hosts.

    It is possible the set of groups may contain a None. This refers to a group
    whose 'ungrouped' attribute is True.

    """
    allowed_group_ids = set()  # If populated, limits the allowed resources to specific group IDs

    inventory_access_perms = {"inventory:*:*", "inventory:*:read", "inventory:hosts:read", "inventory:hosts:*"}
    host_permissions = [p for p in permissions if p.get("permission") in inventory_access_perms]

    if not host_permissions:
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    for perm in host_permissions:
        if not (resourceDefinition := perm["resourceDefinitions"]):
            # Any record with an empty resourceDefinition means
            # unrestricted access.
            # https://insights-rbac.readthedocs.io/en/latest/management.html#resource-definitions
            return set()

        # Get the list of allowed Group IDs from the attribute filter.
        for resourceDefinition in perm["resourceDefinitions"]:
            group_list = _get_group_list_from_resource_definition(resourceDefinition)
            allowed_group_ids.update(group_list)

    return allowed_group_ids


async def query_host_inventory(
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    major: MajorVersion = None,
    minor: MinorVersion = None,
):
    """
    Query the Hosts database for system information on this org's hosts.

    Only return data the authenticated user is permitted to read. Specifically,
    if "host_groups" is not empty (which implies unrestricted access), only
    return hosts that belong to a group present in "host_groups"

    Note there is a special case in the result "get_allowed_host_groups"
    returns, in that the return value may contain (with or without other group
    ids) a None value. If None is present in "host_groups", one of the
    permitted  groups is the "ungrouped" group. While other groups are
    identified by the value of their "id" field, the "ungrouped" group is
    identified by the fact that the value of its "ungrouped" field is `true`.

    """
    if settings.dev:
        org_id = "1234"

    # Build up a query for this org's hosts.
    query = "SELECT * FROM hbi.hosts WHERE org_id = :org_id"

    # #>> '{{operating_system,major}}' fetches the attribute "major" from the
    # "operating_system" subobject in the host's record. This subobject is kept
    # as JSON, and the #>> operator decodes and accesses into it.
    if major is not None:
        query = f"{query} AND system_profile_facts #>> '{{operating_system,major}}' = :major"

    if minor is not None:
        query = f"{query} AND system_profile_facts #>> '{{operating_system,minor}}' = :minor"

    # If host group data is given, we need to filter out hosts that this user
    # is not permitted to see. To do this we add more WHERE clauses to our
    # query.
    if host_groups:
        # the hosts database keeps groups data in a JSONB field, with contents
        # like this:
        # [
        #    {
        #     "account": "123456",
        #     "created": "2025-01-07T12:58:59.569065+00:00",
        #     "host_count": 1,
        #     "id": "f770fbf4-359d-11f0-b21b-5e43c8b8aa2f",
        #     "name": "GroupTwo",
        #     "org_id": "1234",
        #     "ungrouped": false,
        #     "updated": "2025-01-07T12:59:52.471612+00:00"
        #    }
        # ]

        # The following two lines of SQL efficiently search for a match on
        # criteria, and return TRUE if a match is found, FALSE otherwise. Here
        # is how the lines work:
        #
        # * "jsonb_array_elements" queries into the denormalized JSON present
        #   in the "groups" field. In each line the code tests a condition on a
        #   certain field of that json data. The first line is searching for an
        #   "ungrouped" field to have a value of "true", and the second line is
        #   searching for the value held in the "id" field to be present in a
        #   given set of ids.
        # * "SELECT 1" causes the query to stop at the first match it
        #   finds.
        # * "EXISTS" returns a BOOLEAN instead of the result of the query.

        # There is a special case. If None is in host_groups, we must query
        # for a group that has ungrouped == True.
        ungrouped_query = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements(hosts.groups::jsonb) AS group_obj
                    WHERE (group_obj->>'ungrouped')::boolean = true)
        """
        # This query searches for any group record with an id that matches any
        # of our eligible host group ids.
        grouped_query = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements(hosts.groups::jsonb) AS group_obj
                    WHERE group_obj->>'id' = ANY(:host_groups))
        """

        # Here we add our "group" subqueries to the WHERE clause of our final
        # query. If the query contains both a None and string-based group id
        # then the clauses that detect them must be comibined with on OR
        # statement.
        suffix = f" AND {grouped_query}"
        if None in host_groups:
            suffix = f" AND {ungrouped_query}"
            if len(host_groups) > 1:
                # Accept either a group id match or ungrouped = true.
                suffix = f" AND ({ungrouped_query} OR {grouped_query})"

        query += suffix

    result = await session.stream(
        text(textwrap.dedent(query)),
        params={
            "org_id": org_id,
            "major": str(major),
            "minor": str(minor),
            "host_groups": list(host_groups),
        },
    )
    yield result


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
    """Return a callable that gets the specific attributes and returns them
    as a tuple for the purpose of sorting.

    Values of None and "" are sorted lower than other integers
    """

    def _getter(item):
        sort_order = []
        for a in (attr, *attrs):
            current_attr = getattr(item, a)
            if current_attr is None:
                sort_order.append(-2)
            elif current_attr == "":
                sort_order.append(-1)
            else:
                sort_order.append(current_attr)

        return tuple(sort_order)

    return _getter


def ensure_date(value: str | date):
    """Ensure the date value is a date object."""
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Date must be in ISO 8601 format")


def _normalize_version(stream: str) -> t.Tuple[int, int, int]:
    """Returns a tuple of major, minor and micro for a given stream."""
    if stream.casefold() == "rhel8":
        return (8, 0, 0)

    versions = stream.split(".")
    versions.reverse()
    major = int(versions.pop())
    minor = int(versions.pop()) if versions else 0
    micro = int(versions.pop()) if versions else 0

    return (major, minor, micro)


def streams_lt(a: str, b: str):
    """Return True if stream a is less than stream b."""
    try:
        return _normalize_version(a) < _normalize_version(b)
    except ValueError:
        return a < b


def rhel_major_minor(system_profile: dict) -> tuple[int, int | None]:
    # First, try operating_system
    if (operating_system := system_profile.get("operating_system")) is not None:
        major = operating_system.get("major")
        minor = operating_system.get("minor")

        if major is not None:
            return (major, minor)

    # If we don't have the data in operating_system, fall back to os_release
    if (os_release := system_profile.get("os_release")) is not None:
        major, minor = tuple(int(n) for n in os_release.split("."))[:2]
        return (major, minor)

    raise ValueError
