#!/usr/bin/env python
# Show the long and short (seven character) hash. The long hash is needed
# for app-interface, the short hash is useful for checking the container image.
import shutil
import subprocess
import sys


def _run(command: list[str]) -> str:
    return subprocess.check_output(command, text=True)


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
    out = _run(cmd)

    print(f"The latest safe to release commit is {out.strip()} ({out[:7]})")


if __name__ == "__main__":
    main()
