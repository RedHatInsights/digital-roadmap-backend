#!/usr/bin/env python

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

from urllib.error import HTTPError


token = os.getenv("GITLAB_TOKEN", "")
if not token:
    sys.exit("Missing GITLAB_TOKEN")


def gitlab_api(path: str, method: str = "GET"):
    url = f"https://gitlab.cee.redhat.com/api/v4/{path}"
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
        sys.exit(f"{err.code} {err.reason}: {url}")

    return data


def resolve_project_id(name: str) -> int:
    encoded_path = urllib.parse.quote(name, safe="")

    project = gitlab_api(f"projects/{encoded_path}")

    return project["id"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--project-id", "-p", type=int, default=116489)
    group.add_argument("--name", "-n", type=str)
    args = parser.parse_args()

    project_id = args.project_id
    if args.name:
        project_id = resolve_project_id(args.name)
        print(f"Resolved '{args.name}' to ID {project_id}.")

    mirror_path = f"projects/{project_id}/mirror/pull"
    last_mirror = gitlab_api(mirror_path)
    print(f"Last mirror update {last_mirror['last_successful_update_at']}")

    print("Triggering an update...")
    gitlab_api(mirror_path, "POST")
