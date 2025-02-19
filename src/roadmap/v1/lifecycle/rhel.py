import logging
import typing as t

from collections import defaultdict
from operator import attrgetter

from fastapi import APIRouter
from fastapi import Header
from fastapi import Path
from pydantic import BaseModel

from roadmap.common import get_system_count_from_inventory
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import HostCount
from roadmap.models import LifecycleKind
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
    data: list[System]
    total: int


class LifecycleResponse(BaseModel):
    data: list[RHELLifecycle]


@router.get("/", summary="Return lifecycle data for all RHEL versions", response_model=LifecycleResponse)
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


@relevant.get("/")
async def get_relevant_systems(
    authorization: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    user_agent: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
) -> RelevantSystemsResponse:
    headers = {
        "Authorization": authorization,
        "User-Agent": user_agent,
        "X-RH-Identity": x_rh_identity,
    }
    systems_response = await get_system_count_from_inventory(headers)

    system_counts = defaultdict(int)
    for result in systems_response.get("results", []):
        system_profile = result["system_profile"]
        if not system_profile:
            logger.info("Unable to get relevant systems due to missing system profile")
            continue

        name = system_profile.get("operating_system", {}).get("name")
        if name is None:
            logger.info("Unable to get relevant systems due to missing OS from system profile")
            continue

        installed_products = system_profile.get("installed_products", [{}])
        major = system_profile.get("operating_system", {}).get("major")

        # Use minor from RHSM version in order to calculate the correct end date.
        # The minor from RHSM indicates that the system is pinned to a
        # specific minor RHEL version.
        rhsm_version = system_profile.get("rhsm", {}).get("version", "")
        lifecycle_type = get_lifecycle_type(installed_products)
        minor = rhsm_version.partition(".")[-1] or None

        count_key = HostCount(name=name, major=major, minor=minor, lifecycle=lifecycle_type)
        system_counts[count_key] += 1

    results = []
    logger.debug(system_counts.keys())
    for count_key, count in system_counts.items():
        major = count_key.major
        minor = count_key.minor
        lifecycle_type = count_key.lifecycle

        key = str(major) if minor is None else f"{major}.{minor}"
        logger.debug(key)
        try:
            lifecycle_info = OS_LIFECYCLE_DATES[key]
        except KeyError:
            logger.error(f"Missing lifecycle data for RHEL {key}")
            release_date = "Unknown"
            retirement_date = "Unknown"
        else:
            release_date = lifecycle_info.start
            retirement_date = lifecycle_info.end

            if lifecycle_type == LifecycleKind.els:
                retirement_date = lifecycle_info.end_els

            if lifecycle_type == LifecycleKind.e4s:
                retirement_date = lifecycle_info.end_e4s

        results.append(
            System(
                name=count_key.name,
                major=major,
                minor=minor,
                lifecycle_type=lifecycle_type,
                release_date=release_date,
                retirement_date=retirement_date,
                count=count,
            )
        )

    return RelevantSystemsResponse(
        total=sum(system.count for system in results),
        data=sorted(results, key=sort_null_version("lifecycle_type", "major", "minor"), reverse=True),
    )


# @relevant.get("/{major}")
# async def get_relevant_systems_major(major: t.Annotated[int, MajorVersion]) -> RelevantSystemsResponse:
#     systems = get_systems_data(major)
#
#     return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


# @relevant.get("/{major}/{minor}")
# async def get_relevant_systems_major_minor(
#     major: MajorVersion,
#     minor: MinorVersion,
# ) -> RelevantSystemsResponse:
#     systems = get_systems_data(major, minor)
#
#     return sorted(systems, key=attrgetter("major", "minor"), reverse=True)


def get_lifecycle_type(products: list[dict[str, str]]) -> LifecycleKind:
    """Calculate lifecycle type based on the product ID.

    https://downloads.corp.redhat.com/internal/products

    Mainline < EUS (73) < ELS(204) < E4S < EELS
    If 73 in installed_product --> EUS
    If 204 in installed_product --> ELS
    If ??? in installed_product --> EELS
    If ??? in installed_product --> E4S

    """
    ids = {item.get("id") for item in products}
    type = LifecycleKind.mainline

    if "73" in ids:
        type = LifecycleKind.eus

    if "204" in ids:
        type = LifecycleKind.els

    return type


def sort_null_version(attr, /, *attrs) -> t.Callable:
    def _getter(item):
        # If an attribute is None, use a 0 instead of None for the purpose of sorting
        return tuple(getattr(item, a) or 0 for a in (attr, *attrs))

    return _getter
