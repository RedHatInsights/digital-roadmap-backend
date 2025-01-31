#!/usr/bin/env python
import argparse
import shutil
import subprocess

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def freeze(python_version: str, requirement: Path) -> str:
    print(f"🥶 Freezing Python {python_version} {requirement.stem}...", flush=True)

    python_bin = shutil.which(f"python{python_version}")
    if python_bin is None:
        return f"Unable to find Python{python_version}"

    python_bin = Path(python_bin)

    repo_root = requirement.parent.parent
    venv_path = repo_root / ".venvs" / f"freezer-{requirement.stem}-{python_version}"
    venv_python = venv_path / "bin" / "python"
    constraints = repo_root / "requirements" / "constraints.txt"
    freeze_file = repo_root / "requirements" / f"{requirement.stem}-{python_version}.txt"

    # Create a fresh virtual environment
    subprocess.check_output([python_bin, "-m", "venv", "--clear", "--system-site-packages", venv_path])
    subprocess.check_output([venv_python, "-m", "pip", "install", "--upgrade", "pip"])

    # Install requirements with constraints
    subprocess.check_output(
        [venv_python, "-m", "pip", "install", "--requirement", requirement, "--constraint", constraints]
    )

    # Generate a freeze file
    result = subprocess.run([venv_python, "-m", "pip", "freeze"], check=True, capture_output=True)
    header = b""
    if requirement.stem.endswith("-dev"):
        reqs_header = f"-r requirements-{python_version}.txt\n".encode("utf-8")
        test_header = f"-r requirements-test-{python_version}.txt\n".encode("utf-8")
        header = reqs_header + test_header

    freeze_file.write_bytes(header + result.stdout)

    return f"✅ {requirement.stem}-{python_version} complete"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-versions", default="3.12,3.13")

    return parser.parse_args()


def sort_versions(versions: str) -> list[str]:
    def list_of_parts(items):
        return [int(n) for n in items.split(".")]

    stripped_versions = [version.strip() for version in versions.split(",")]
    return sorted(stripped_versions, key=list_of_parts)


def main():
    args = parse_args()
    file = Path(__file__)
    repo_root = file.parent.parent
    requirements = repo_root.joinpath("requirements").glob("*.in")
    python_versions = sort_versions(args.python_versions)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(freeze, py_ver, req)
            for req in requirements
            for py_ver in python_versions  # noformat
        ]
    for future in as_completed(futures):
        print(future.result())

    # Put requirements for the main Python version in the repo root for convenience.
    target_python_version = "3.12"
    shutil.copy(repo_root / "requirements" / f"requirements-{target_python_version}.txt", "requirements.txt")


if __name__ == "__main__":
    main()
