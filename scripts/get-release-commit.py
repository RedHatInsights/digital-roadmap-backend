#!/usr/bin/env python
# Show the long and short (seven character) hash. The long hash is needed
# for app-interface, the short hash is useful for checking the container image.
import json
import shutil
import subprocess
import sys
import urllib.request


def _run(command: list[str]) -> str:
    return subprocess.check_output(command, text=True)


def check_image_tag(repository: str, tag: str) -> None:
    quay_api_url = f"https://quay.io/api/v1/repository/{repository}/tag/"

    try:
        with urllib.request.urlopen(quay_api_url) as response:
            data = response.read()
    except urllib.request.HTTPError as err:
        sys.exit(f"Error trying to get tags for {repository}: {err}")

    tags = json.loads(data).get("tags", {})
    short_tags = {tag["name"] for tag in tags if len(tag["name"]) <= 10}
    if tag not in short_tags:
        sys.exit(f"Unable to find tag '{tag}' in quay.io/{repository}\nCurrent Tags: {', '.join(short_tags)}")


def main() -> None:
    git = shutil.which("git")
    if git is None:
        sys.exit("Unable to find git")

    # Get the upstream of the main branch
    cmd = [git, "for-each-ref", "--format", "%(upstream:short)", "refs/heads/main"]
    upstream_name = _run(cmd).split("/", 1)[0]

    # Fetch changes from the remote
    _run([git, "fetch", upstream_name])

    cmd = [
        git,
        "log",
        "--format=%H",
        "--no-merges",
        f"{upstream_name}/main",
        "--max-count=1",
    ]
    commit_hash = _run(cmd)
    short_hash = commit_hash[:7]

    check_image_tag("redhat-services-prod/rhel-lightspeed-tenant/roadmap", short_hash)
    print(f"The latest safe to release commit is {commit_hash.strip()} ({short_hash})")


if __name__ == "__main__":
    main()
