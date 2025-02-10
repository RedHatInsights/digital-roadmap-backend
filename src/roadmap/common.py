import typing as t
import urllib.parse
import urllib.request


async def get_all_systems(headers: dict[t.Any, t.Any]):
    params = {
        "per_page": 5,
        "page": 1,
        # "staleness": ["fresh", "stale", "stale_warning"],
        "order_by": "operating_system",
    }
    req = urllib.request.Request(
        # f"https://console.redhat.com/api/inventory/v1/system_profile/operating_system?{urllib.parse.urlencode(params)}",
        f"https://httpbin.org/get?{urllib.parse.urlencode(params)}",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = response.read()
    except urllib.error.HTTPError as err:
        return {"error": str(err)}

    return data
