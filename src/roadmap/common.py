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
async def get_system_count_from_inventory(headers: dict[str, str | None]) -> dict[str, t.Any]:
    if SETTINGS.dev:
        logger.debug("Running in development mode. Returning fixture response data for inventory.")
        file = Path(__file__).resolve()
        response_data = file.parent.parent.parent / "tests" / "fixtures" / "inventory_response.json"
        return json.loads(response_data.read_text())

    if not headers.get("Authorization"):
        # If we don't have a token, do not try to query the API.
        # This could be a dev/test environment.
        logger.info("Missing authorization header. Unable to get inventory.")
        return {}

    # Filter out missing header values
    headers = {k: v for k, v in headers.items() if v is not None}
    params = {
        "per_page": 100,
        "page": 100,
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
