#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import base64
import pathlib
import sys
import textwrap
import urllib.request
import uuid

from urllib.error import HTTPError

from app_common_python import json


try:
    import argcomplete
except ImportError:
    argcomplete = None


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--org-id", help="Org ID", required=True, type=int)
    parser.add_argument("-e", "--environment", choices=["prod", "stage"], default="prod")
    parser.add_argument("-n", "--display-name", help="Filter by display_name")
    parser.add_argument("-l", "--limit", type=int, help="Maximum number of records to retrieve")
    parser.add_argument("-s", "--scrub", action="store_true", help="Anonymize the data")

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser.parse_args()


def get_token(environment: str):
    token_file = pathlib.Path(f"~/.config/tokens/openshift-token-{environment}").expanduser()
    if not token_file.exists():
        sys.exit(f"Missing token file. Please run 'oc whoami -t > {token_file}'")

    return token_file.read_text().strip()


def query_gabi(environment: str, query: str, offset: int = 0, limit: int = 100):
    urls = {
        "stage": b"aHR0cHM6Ly9nYWJpLWhvc3QtaW52ZW50b3J5LXN0YWdlLmFwcHMuY3JjczAydWUxLnVyYnkucDEub3BlbnNoaWZ0YXBwcy5jb20vcXVlcnk/YmFzZTY0X3F1ZXJ5PXRydWU=",
        "prod": b"aHR0cHM6Ly9nYWJpLWhvc3QtaW52ZW50b3J5LXByb2QuYXBwcy5jcmNwMDF1ZTEubzltOC5wMS5vcGVuc2hpZnRhcHBzLmNvbS9xdWVyeT9iYXNlNjRfcXVlcnk9dHJ1ZQ==",
    }
    url = base64.b64decode(urls[environment]).decode("ascii")

    headers = {
        "Authorization": f"Bearer {get_token(environment)}",
        "Content-Type": "application/json",
    }
    query = textwrap.dedent(query).replace("\n", " ").strip()
    b_query = bytes(f"{query} LIMIT {limit} OFFSET {offset}", "utf-8")
    b_query = base64.b64encode(b_query)

    query = textwrap.dedent(b_query.decode("utf-8"))
    body = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(url, body, headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        message = err
        if err.code == 403:
            message = f"{err}. Renew your token with 'oc whoami -t'."

        sys.exit(str(message))

    return data["result"]


def host_count(environment: str, org_id: int) -> int:
    query = f"SELECT COUNT(*) from hbi.hosts WHERE org_id = '{org_id}'"
    result = query_gabi(environment, query)
    return int(result[1][0])


def main():  # noqa: C901
    args = parse_args()

    environment = args.environment
    org_id = args.org_id
    scrub = args.scrub
    display_name = args.display_name
    limit = args.limit

    total_hosts = host_count(environment, org_id)
    total_limit = limit or total_hosts
    print(f"There are {total_hosts:,} hosts in inventory for org {org_id}.")
    if limit:
        print(f"Limiting to the first {total_limit} records.")

    query = f"""
    SELECT
        id,
        display_name,
        system_profile_facts
    FROM hbi.hosts
    WHERE org_id = '{org_id}'
    ORDER BY id
    """
    if display_name:
        insertion_point = query.index("ORDER BY")
        query = query[:insertion_point] + f"AND display_name = '{display_name}'\n" + query[insertion_point:]

    offset = 0
    remaining = total_limit
    results = []
    keys_to_keep = {
        "system_profile_facts",
        "id",
        "dnf_modules",
        "installed_packages",
        "rhsm",
        "owner_id",
        "os_release",
        "operating_system",
        "releasever",
    }
    while remaining > 0:
        query_limit = 100
        if remaining < 100:
            query_limit = remaining

        response = query_gabi(environment, query, offset, query_limit)
        headers = response[0]
        records = response[1:]

        for record in records:
            inner_record = {}
            for idx, data in enumerate(record):
                field = headers[idx]
                if scrub:
                    if field not in keys_to_keep:
                        continue

                    if field == "id":
                        data = str(uuid.uuid4())

                if field == "system_profile_facts":
                    data = json.loads(data)
                    if scrub:
                        data = {key: value for key, value in data.items() if key in keys_to_keep}
                        data["owner_id"] = str(uuid.uuid4())

                inner_record[field] = data

            results.append(inner_record)

        offset += 100
        remaining -= len(records)
        if display_name:
            # Avoid an infinite loop when filtering by display name.
            # If there are more than 100 records with the same display_name, this
            # will need to be improved to account for that.
            break

    scratch = pathlib.Path(__file__).parents[1] / "scratch"
    scratch.mkdir(exist_ok=True)

    output = scratch / f"hosts-{org_id}.json"
    output.write_text(json.dumps(results, indent=4))

    print(f"Got {len(results)} records for org {org_id}.")
    print(output)


if __name__ == "__main__":
    main()
