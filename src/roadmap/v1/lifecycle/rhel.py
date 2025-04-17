import logging
import typing as t

from collections import defaultdict
from operator import attrgetter

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.common import check_inventory_access
from roadmap.common import decode_header
from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.common import query_rbac
from roadmap.common import sort_attrs
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.database import get_db
from roadmap.models import HostCount
from roadmap.models import LifecycleType
from roadmap.models import Meta
from roadmap.models import RHELLifecycle
from roadmap.models import System


logger = logging.getLogger("uvicorn.error")


router = APIRouter(
    prefix="/rhel",
    tags=["RHEL"],
)

MajorVersion = t.Annotated[int, Path(description="Major version number", ge=8, le=10)]
MinorVersion = t.Annotated[int, Path(description="Minor version number", ge=0, le=10)]


class RelevantSystemsResponse(BaseModel):
    meta: Meta
    data: list[System]


class LifecycleResponse(BaseModel):
    data: list[RHELLifecycle]


@router.get("", summary="Return lifecycle data for all RHEL versions", response_model=LifecycleResponse)
async def get_systems():
    return {"data": get_lifecycle_data()}


@router.get("/{major}", response_model=LifecycleResponse)
async def get_systems_major(
    major: MajorVersion,
):
    return {"data": get_lifecycle_data(major)}


@router.get("/{major}/{minor}", response_model=LifecycleResponse)
async def get_systems_major_minor(
    major: MajorVersion,
    minor: MinorVersion,
):
    return {"data": get_lifecycle_data(major, minor)}


def get_lifecycle_data(major: int | None = None, minor: int | None = None, reverse: bool = True):
    lifecycles = (item for item in OS_LIFECYCLE_DATES.values() if item.minor is not None)

    if major and minor is not None:
        lifecycles = (item for item in lifecycles if (item.major, item.minor) == (major, minor))
    elif major:
        lifecycles = (item for item in lifecycles if item.major == major)

    return sorted(lifecycles, key=attrgetter("major", "minor"), reverse=reverse)


## Relevant ##
relevant = APIRouter(
    prefix="/relevant/lifecycle/rhel",
    tags=["Relevant", "RHEL"],
)


@relevant.get("/{major}/{minor}")
@relevant.get("/{major}")
@relevant.get("")
async def get_relevant_systems(  # noqa: C901
    session: t.Annotated[AsyncSession, Depends(get_db)],
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    major: int | None = None,
    minor: int | None = None,
) -> RelevantSystemsResponse:
    org_id = decode_header(x_rh_identity)
    rbac_response = await query_rbac(x_rh_identity)
    can_access_inventory, resource_groups = await check_inventory_access(rbac_response)
    if not can_access_inventory:
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    systems_response = query_host_inventory(
        session=session, org_id=org_id, major=major, minor=minor, groups=resource_groups
    )

    system_counts = defaultdict(int)
    missing = defaultdict(int)
    async for result in systems_response:
        system_profile = result.get("system_profile_facts")
        if not system_profile:
            missing["system_profile"] += 1
            continue

        name = system_profile.get("operating_system", {}).get("name")
        if name is None:
            missing["os_profile"] += 1
            continue

        installed_products = system_profile.get("installed_products", [{}])
        os_major = system_profile.get("operating_system", {}).get("major")
        os_minor = system_profile.get("operating_system", {}).get("minor")
        lifecycle_type = get_lifecycle_type(installed_products)

        count_key = HostCount(name=name, major=os_major, minor=os_minor, lifecycle=lifecycle_type)
        system_counts[count_key] += 1

    results = []
    for count_key, count in system_counts.items():
        key = str(count_key.major) if count_key.minor is None else f"{count_key.major}.{count_key.minor}"
        try:
            lifecycle_info = OS_LIFECYCLE_DATES[key]
        except KeyError:
            logger.error(f"Missing lifecycle data for RHEL {key}")
            release_date = "Unknown"
            retirement_date = "Unknown"
        else:
            release_date = lifecycle_info.start
            retirement_date = lifecycle_info.end

            if count_key.lifecycle == LifecycleType.els:
                retirement_date = lifecycle_info.end_els

            if count_key.lifecycle == LifecycleType.e4s:
                retirement_date = lifecycle_info.end_e4s

        results.append(
            System(
                name=count_key.name,
                major=count_key.major,
                minor=count_key.minor,
                lifecycle_type=count_key.lifecycle,
                release_date=release_date,
                retirement_date=retirement_date,
                count=count,
            )
        )

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    return RelevantSystemsResponse(
        meta=Meta(total=sum(system.count for system in results), count=len(results)),
        data=sorted(results, key=sort_attrs("lifecycle_type", "major", "minor"), reverse=True),
    )
