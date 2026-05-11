#!/usr/bin/env python3
"""Stamp deployment dates on roadmap items.

For each roadmap item in upcoming.json that doesn't have a deployedDate,
set it to today's date. This should be run during container image build
to mark when new items were deployed.

Items that already have a deployedDate are left unchanged, preserving
their original deployment timestamp.
"""

import json
import sys

from datetime import date
from pathlib import Path


def stamp_deployment_dates(file_path: Path, deployment_date: date | None = None) -> int:
    """
    Stamp deployment dates on roadmap items.

    Args:
        file_path: Path to the upcoming.json file
        deployment_date: Date to use for deployment (defaults to today)

    Returns:
        Number of items that were stamped with a new deployment date
    """
    if deployment_date is None:
        deployment_date = date.today()

    deployment_date_str = deployment_date.isoformat()

    # Read the JSON data
    with open(file_path) as f:
        items = json.load(f)

    stamped_count = 0

    # Stamp items that don't have a deployedDate
    for item in items:
        details = item.get("details", {})
        if details.get("deployedDate") is None:
            details["deployedDate"] = deployment_date_str
            stamped_count += 1

    # Write the updated JSON back
    with open(file_path, "w") as f:
        json.dump(items, f, indent=2)
        f.write("\n")  # Add trailing newline

    return stamped_count


def main():
    if len(sys.argv) < 2:
        print("Usage: stamp-deployment-date.py <path-to-upcoming.json> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    deployment_date = None
    if len(sys.argv) >= 3:
        try:
            deployment_date = date.fromisoformat(sys.argv[2])
        except ValueError:
            print(f"Error: Invalid date format: {sys.argv[2]} (expected YYYY-MM-DD)", file=sys.stderr)
            sys.exit(1)

    stamped_count = stamp_deployment_dates(file_path, deployment_date)
    print(f"Stamped {stamped_count} roadmap items with deployment date: {deployment_date or date.today()}")


if __name__ == "__main__":
    main()
