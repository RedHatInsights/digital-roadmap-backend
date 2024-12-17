#!/usr/bin/env python

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    # venv.create(venv_path, with_pip=True, system_site_packages=True, clear=True)
    subprocess.check_output([python_bin, "-m", "venv", "--clear", "--system-site-packages", venv_path])
    subprocess.check_output([venv_python, "-m", "pip", "install", "--upgrade", "pip"])

    # Install requirements with constraints
    subprocess.check_output(
        [venv_python, "-m", "pip", "install", "--requirement", requirement, "--constraint", constraints]
    )

    # Generate a freeze file
    result = subprocess.run([venv_python, "-m", "pip", "freeze"], check=True, capture_output=True)
    freeze_file.write_bytes(result.stdout)

    return f"✅ {requirement.stem}-{python_version} complete"


def main():
    file = Path(__file__)
    repo_root = file.parent.parent
    requirements = repo_root.joinpath("requirements").glob("*.in")
    python_versions = {"3.9", "3.11", "3.12"}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(freeze, py_ver, req)
            for req in requirements
            for py_ver in python_versions  # noformat
        ]
    for future in as_completed(futures):
        print(future.result())

    target_python_version = "3.9"
    shutil.copy(repo_root / "requirements" / f"requirements-{target_python_version}.txt", "requirements.txt")


if __name__ == "__main__":
    main()