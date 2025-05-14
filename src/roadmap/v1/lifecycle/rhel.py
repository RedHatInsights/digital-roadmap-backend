import logging
import typing as t

from collections import defaultdict
from datetime import date

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from pydantic import BaseModel

from roadmap.common import decode_header
from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.common import sort_attrs
from roadmap.data.systems import OS_LIFECYCLE_DATES
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

MajorVersion = t.Annotated[int | None, Path(description="Major version number", ge=8, le=10)]
MinorVersion = t.Annotated[int | None, Path(description="Minor version number", ge=0, le=10)]


class RelevantSystemsResponse(BaseModel):
    meta: Meta
    data: list[System]


class LifecycleResponse(BaseModel):
    data: list[RHELLifecycle]


def get_lifecycle_data(
    major: int | None = None,
    minor: int | None = None,
    reverse: bool = True,
):
    lifecycles = (item for item in OS_LIFECYCLE_DATES.values())

    if major and minor is not None:
        lifecycles = (item for item in lifecycles if (item.major, item.minor) == (major, minor))
    elif major:
        lifecycles = (item for item in lifecycles if item.major == major)

    return sorted(lifecycles, key=sort_attrs("major", "minor"), reverse=reverse)


@router.get(
    "",
    summary="Return lifecycle data for all RHEL versions",
    response_model=LifecycleResponse,
)
async def get_systems():
    """
    Note: When the minor version is null, that represents the lifecycle dates for the
    entire major version.
    """
    return {"data": get_lifecycle_data()}


@router.get(
    "/full",
    summary="Full lifecycle dates for all major versions of RHEL",
    response_model=LifecycleResponse,
)
async def get_systems_major_full_all():
    lifecycles = (item for item in get_lifecycle_data() if item.minor is None)

    return {"data": lifecycles}


@router.get(
    "/full/{major}",
    summary="Full lifecycle dates for a specific major version of RHEL",
    response_model=LifecycleResponse,
)
async def get_systems_major_full(major: MajorVersion):
    lifecycles = (item for item in get_lifecycle_data(major=major) if item.minor is None)

    return {"data": lifecycles}


@router.get(
    "/{major}",
    summary="RHEL lifecycle dates for a specific major version",
    response_model=LifecycleResponse,
)
async def get_systems_major(
    major: MajorVersion,
):
    """
    Note: When the minor version is null, that represents the lifecycle dates for the
    entire major version.
    """
    return {"data": get_lifecycle_data(major)}


@router.get(
    "/{major}/{minor}",
    summary="RHEL lifecycle dates for a specific major and minor version",
    response_model=LifecycleResponse,
)
async def get_systems_major_minor(
    major: MajorVersion,
    minor: MinorVersion,
):
    return {"data": get_lifecycle_data(major, minor)}


## Relevant ##
relevant = APIRouter(
    prefix="/relevant/lifecycle/rhel",
    tags=["Relevant", "RHEL"],
)


@relevant.get(
    "",
    summary="RHEL lifecycle dates for systems in inventory",
)
async def get_relevant_systems(  # noqa: C901
    org_id: t.Annotated[str, Depends(decode_header)],
    systems: t.Annotated[t.Any, Depends(query_host_inventory)],
    related: bool = False,
) -> RelevantSystemsResponse:
    system_counts = defaultdict(int)
    missing = defaultdict(int)
    systems_by_version_lifecycle = defaultdict(list)
    async for result in systems.mappings():
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

        # Collect system IDs by major version, minor version, and lifecycle type so we can return those in the response
        system_id = result["id"]
        system_id_key = (str(os_major) if os_minor is None else f"{os_major}.{os_minor}", lifecycle_type)
        systems_by_version_lifecycle[system_id_key].append(system_id)

        count_key = HostCount(name=name, major=os_major, minor=os_minor, lifecycle=lifecycle_type)
        system_counts[count_key] += 1

    results = []
    system_keys = set()
    for count_key, count in system_counts.items():
        key = str(count_key.major) if count_key.minor is None else f"{count_key.major}.{count_key.minor}"
        system_id_key = (key, count_key.lifecycle)
        system_keys.add(key)
        try:
            lifecycle_info = OS_LIFECYCLE_DATES[key]
        except KeyError:
            logger.warning(f"Missing lifecycle data for RHEL {key}")
            start_date = "Unknown"
            end_date = "Unknown"
        else:
            start_date = lifecycle_info.start_date
            end_date = lifecycle_info.end_date

            if count_key.lifecycle == LifecycleType.els:
                end_date = lifecycle_info.end_date_els

            if count_key.lifecycle == LifecycleType.e4s:
                end_date = lifecycle_info.end_date_e4s

        results.append(
            System(
                name=count_key.name,
                major=count_key.major,
                minor=count_key.minor,
                lifecycle_type=count_key.lifecycle,
                start_date=start_date,
                end_date=end_date,
                count=count,
                related=False,
                systems=systems_by_version_lifecycle[system_id_key],
            )
        )

    if related:
        relateds = set()
        today = date.today()
        for count_key, count in system_counts.items():
            minor = count_key.minor if count_key.minor is not None else -1
            for key, rhel in OS_LIFECYCLE_DATES.items():
                rhel_minor = rhel.minor if rhel.minor is not None else -1
                if rhel.major == count_key.major and rhel_minor > minor and rhel.end_date > today:
                    relateds.add(key)
        relateds -= system_keys
        for key in relateds:
            os = OS_LIFECYCLE_DATES[key]
            results.append(
                System(
                    name=os.name,
                    major=os.major,
                    minor=os.minor,
                    lifecycle_type=LifecycleType.mainline,
                    start_date=os.start_date,
                    end_date=os.end_date,
                    count=0,
                    related=True,
                )
            )

    if missing:
        missing_items = ", ".join(f"{key}: {value}" for key, value in missing.items())
        logger.info(f"Missing {missing_items} for org {org_id or 'UNKNOWN'}")

    return RelevantSystemsResponse(
        meta=Meta(total=sum(system.count for system in results), count=len(results)),
        data=sorted(results, key=sort_attrs("lifecycle_type", "major", "minor"), reverse=True),
    )
