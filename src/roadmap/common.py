import json
import typing as t
import urllib.parse
import urllib.request

from urllib.error import HTTPError

from starlette.datastructures import Headers


# FIXME: This should be cached
async def get_system_count_from_inventory(headers: Headers) -> dict[str, t.Any]:
    # When Host has "localhost" in it, an error is returned.
    # Only include the headers that are necessary.
    # This could also change to excluding problematic headers.
    include = ["user-agent", "authorization"]
    hdrs = {k: v for k, v in headers.items() if k in include}

    if "authorization" not in hdrs:
        # If we don't have a token, do not try to query the API.
        # This could be a dev/test environment.
        return {}

    params = {
        "per_page": 100,
        "page": 1,
        "staleness": ["fresh", "stale", "stale_warning"],
        "order_by": "operating_system",
    }
    req = urllib.request.Request(
        f"https://console.redhat.com/api/inventory/v1/system_profile/operating_system?{urllib.parse.urlencode(params, doseq=True)}",
        headers=hdrs,
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        return {"error": str(err)}

    return data
