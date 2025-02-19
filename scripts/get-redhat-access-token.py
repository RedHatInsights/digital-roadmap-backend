#!/usr/bin/env python

import json
import os
import sys
import urllib.parse
import urllib.request

from urllib.error import HTTPError


def main():
    offline_token = os.getenv("RH_OFFLINE_TOKEN")
    if offline_token is None:
        sys.exit(
            "RH_OFFLINE_TOKEN is not set."
            "\nCreate an offline token by following the directions at "
            "https://access.redhat.com/articles/3626371."
        )

    # Get a new auth token that expires in 15 minutes
    url = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
    values = {
        "grant_type": "refresh_token",
        "client_id": "rhsm-api",
        "refresh_token": offline_token,
    }
    data = urllib.parse.urlencode(values)
    b_data = data.encode("ascii")
    req = urllib.request.Request(url, b_data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            response_data = json.load(response)
    except HTTPError as err:
        sys.exit(f"Unable to get token. {err}")

    print(response_data["access_token"])


if __name__ == "__main__":
    main()
