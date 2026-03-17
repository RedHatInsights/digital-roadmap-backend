#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import base64
import os
import pathlib
import sys
import textwrap
import tomllib
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
    parser.add_argument("-n", "--display-name", help="Filter by display names that start with the provided value.")
    parser.add_argument("-l", "--limit", type=int, help="Maximum number of records to retrieve")
    parser.add_argument("-s", "--scrub", action="store_true", help="Anonymize the data")

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser.parse_args()


def load_config():
    config_path = pathlib.Path(__file__).parents[1] / ".config.toml"
    if env_path := os.getenv("ROADMAP_DEV_CONFIG"):
        config_path = pathlib.Path(env_path).resolve()

    if not config_path.exists():
        sys.exit(f"Missing config file '{config_path.name}'")

    return tomllib.loads(config_path.read_text())


def get_token(environment: str):
    token_file = pathlib.Path(f"~/.config/tokens/openshift-token-{environment}").expanduser()
    if not token_file.exists():
        sys.exit(f"Missing token file. Please run 'oc whoami -t > {token_file}'")

    return token_file.read_text().strip()


def query_gabi(environment: str, query: str, offset: int = 0, limit: int = 100):
    config = load_config()

    url = f"{config['environments'][environment]}?base64_query=true"
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
        h.id,
        h.display_name,
        sps.operating_system,
        sps.os_release,
        sps.dnf_modules,
        spd.installed_packages,
        spd.installed_products
    FROM hbi.hosts h
        INNER JOIN hbi.system_profiles_static sps
            ON h.id = sps.host_id
            AND h.org_id = sps.org_id
        LEFT JOIN hbi.system_profiles_dynamic spd
            ON h.id = spd.host_id
            AND h.org_id = spd.org_id
    WHERE h.org_id = '{org_id}'
    ORDER BY h.id
    """
    if display_name:
        insertion_point = query.index("ORDER BY")
        query = (
            query[:insertion_point] + f"AND starts_with(h.display_name, '{display_name}')\n" + query[insertion_point:]
        )

    offset = 0
    remaining = total_limit
    results = []
    # Columns from the split profile tables (system_profiles_static, system_profiles_dynamic)
    profile_fields = {"operating_system", "os_release", "dnf_modules", "installed_packages", "installed_products"}
    # JSONB columns need json.loads(); os_release is a plain varchar and does not
    jsonb_fields = {"operating_system", "dnf_modules", "installed_packages", "installed_products"}
    # When scrubbing, only keep these profile fields in the output
    profile_keys_to_keep = {"dnf_modules", "installed_packages", "os_release", "operating_system"}

    while remaining > 0:
        query_limit = 100
        if remaining < 100:
            query_limit = remaining

        response = query_gabi(environment, query, offset, query_limit)
        headers = response[0]
        records = response[1:]

        for record in records:
            inner_record = {}
            system_profile = {}
            for idx, data in enumerate(record):
                field = headers[idx]

                # Collect profile columns into a nested dict, parsing JSONB strings
                if field in profile_fields:
                    if data and field in jsonb_fields:
                        data = json.loads(data)
                    if not scrub or field in profile_keys_to_keep:
                        system_profile[field] = data

                # Host-level fields: anonymize id and strip display_name when scrubbing
                else:
                    if scrub:
                        if field == "display_name":
                            continue
                        if field == "id":
                            data = str(uuid.uuid4())
                    inner_record[field] = data

            inner_record["system_profile"] = system_profile
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
