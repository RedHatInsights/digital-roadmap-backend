#!/usr/bin/env python

import argparse
import json
import os
import sys
import urllib.request

from urllib.error import HTTPError


token = os.getenv("GITLAB_TOKEN", "")
if not token:
    sys.exit("Missing GITLAB_TOKEN")


def gitlab_mirror_api(project_id: str, method: str = "GET"):
    url = f"https://gitlab.cee.redhat.com/api/v4/projects/{project_id}/mirror/pull"
    headers = {
        "PRIVATE-TOKEN": token,
    }
    req = urllib.request.Request(
        url,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        sys.exit(err.msg)

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", "-p", type=str, default="116489")
    args = parser.parse_args()

    last_mirror = gitlab_mirror_api(project_id=args.project_id)
    print(f"Last mirror update {last_mirror['last_successful_update_at']}")

    print("Triggering an update...")
    gitlab_mirror_api(args.project_id, "POST")
