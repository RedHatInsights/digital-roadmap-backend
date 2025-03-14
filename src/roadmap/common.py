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

from roadmap.config import SETTINGS
from roadmap.models import LifecycleType


logger = logging.getLogger("uvicorn.error")


# FIXME: This should be cached
async def query_host_inventory(
    headers: dict[str, str | None],
    page: int = 1,
    per_page: int = 100,
    major: int | None = None,
    minor: int | None = None,
) -> dict[str, t.Any]:
    if SETTINGS.dev:
        logger.debug("Running in development mode. Returning fixture response data for inventory.")
        file = Path(__file__).resolve()
        logger.debug(f"{major=} {minor=}")
        response_data_file = file.parent.parent.parent / "tests" / "fixtures" / "inventory_response_packages.json.gz"
        with gzip.open(response_data_file) as gzfile:
            response_data = json.load(gzfile)
        if major is not None:
            filtered_results = [
                item
                for item in response_data["results"]
                if item.get("system_profile", {}).get("operating_system", {}).get("major") == major
            ]
            response_data["results"] = filtered_results

        if minor is not None:
            filtered_results = [
                item
                for item in response_data["results"]
                if item.get("system_profile", {}).get("operating_system", {}).get("minor") == minor
            ]
            response_data["results"] = filtered_results

        return response_data

    if not headers.get("Authorization"):
        # If we don't have a token, do not try to query the API.
        # This could be a dev/test environment.
        logger.info("Missing authorization header. Unable to get inventory.")
        return {}

    # Filter out missing header values
    headers = {k: v for k, v in headers.items() if v is not None}
    params = {
        "per_page": per_page,
        "page": page,
        "staleness": ["fresh", "stale", "stale_warning"],
        "order_by": "updated",
        "fields[system_profile]": ",".join(
            # TODO: Make these fields a parameter
            [
                "dnf_modules",
                "operating_system",
                "rhsm",
                "installed_packages",
                "installed_products",
            ]
        ),
    }
    if any(value is not None for value in (major, minor)):
        # Build the filter value of either "{major}" or "{major}.{minor}",
        # such as "9", or "9.5".
        params["filter[system_profile][operating_system][RHEL][version][eq]"] = (
            f"{major}{'.' + str(minor) if minor is not None else ''}"
        )

    req = urllib.request.Request(
        f"https://console.redhat.com/api/inventory/v1/hosts?{urllib.parse.urlencode(params, doseq=True)}",
        headers=headers,  # pyright: ignore [reportArgumentType]
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        logger.error(f"Problem getting systems from inventory: {err}")
        raise HTTPException(status_code=err.code, detail=err.msg)

    return data


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


def sort_null_version(attr, /, *attrs) -> t.Callable:
    def _getter(item):
        # If an attribute is None, use a 0 instead of None for the purpose of sorting
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
