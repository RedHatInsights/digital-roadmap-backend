import json
import logging
import typing as t
import urllib.parse
import urllib.request

from pathlib import Path
from urllib.error import HTTPError

from fastapi import HTTPException

from roadmap.config import SETTINGS


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
        response_data_file = file.parent.parent.parent / "tests" / "fixtures" / "inventory_response.json"
        response_data = json.loads(response_data_file.read_text())
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
            [
                "arch",
                # "dnf_modules",
                "operating_system",
                "rhsm",
                # "installed_packages",
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
