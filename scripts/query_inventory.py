#!/usr/bin/env python

import json
import os
import sys
import urllib.parse
import urllib.request

from pathlib import Path
from urllib.error import HTTPError


token = os.getenv("RH_TOKEN")
if token is None:
    sys.exit("Missing RH_TOKEN")

headers = {"Authorization": f"Bearer {token}"}
params = {
    "per_page": 100,
    "page": 1,
    "staleness": ["fresh", "stale", "stale_warning"],
    "order_by": "updated",
    "fields[system_profile]": ",".join(
        [
            "arch",
            "operating_system",
            "rhsm",
            "installed_products",
        ]
    ),
}
req = urllib.request.Request(
    f"https://console.redhat.com/api/inventory/v1/hosts?{urllib.parse.urlencode(params, doseq=True)}",
    headers=headers,
)

try:
    with urllib.request.urlopen(req) as response:
        data = json.load(response)
except HTTPError as err:
    sys.exit(err.msg)

output = Path(__file__).resolve().parent.parent / "scratch" / "response.json"

if not output.parent.exists():
    output.parent.mkdir()

print(f"Writing response to {output}")
output.write_text(json.dumps(data, indent=2) + "\n")
