#!/usr/bin/env python

import subprocess
import sys
import venv
from pathlib import Path


def main():
    file = Path(__file__)
    repo_root = file.parent.parent
    requirements = (
        "requirements",
        "requirements-dev",
    )
    for req in requirements:
        print(f"🥶 Freezing {req}...", end="", flush=True)

        venv_path = repo_root / ".venvs" / f"freezer-{req}-{sys.version_info.major}.{sys.version_info.minor}"
        python_bin = venv_path / "bin" / "python"
        requirements = repo_root / "requirements" / f"{req}.in"
        constraints = repo_root / "requirements" / "constraints.txt"
        freeze_file = repo_root / f"{req}.txt"

        # Create a fresh virtual environment
        venv.create(venv_path, with_pip=True, system_site_packages=True, clear=True)
        subprocess.check_output([python_bin, "-m", "pip", "install", "--upgrade", "pip"])

        # Install requirements with constraints
        subprocess.check_output(
            [python_bin, "-m", "pip", "install", "--requirement", requirements, "--constraint", constraints]
        )

        # Generate a freeze file
        result = subprocess.run([python_bin, "-m", "pip", "freeze"], check=True, capture_output=True)
        freeze_file.write_bytes(result.stdout)

        print("✅")


if __name__ == "__main__":
    main()
