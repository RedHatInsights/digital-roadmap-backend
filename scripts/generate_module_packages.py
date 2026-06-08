#!/usr/bin/env python3
"""
Generate module_packages.py from modulemd YAML files.

This script parses downloaded modulemd files and creates a mapping of
(module_name, os_major, stream) -> set of package names.

Usage:
    1. Run ./download_modulemd.sh to get modules-8.yaml and modules-9.yaml
    2. Run this script: python scripts/generate_module_packages.py
    3. Output: src/roadmap/data/module_packages.py
"""

import re
import sys

from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml


def parse_nevra(nevra_string):
    """Extract package name from NEVRA string.

    Examples:
        mariadb-3:10.11.10-1.module_el9+1141+de86b509.x86_64 -> mariadb
        nginx-1:1.20.1-1.module+el8.5.0+12345.x86_64 -> nginx
        nodejs-20.11.1-1.module+el9.3.0+20363+77c810cf.x86_64 -> nodejs
    """
    # Handle epoch format: name-epoch:version-release.arch
    if ":" in nevra_string:
        # Find the name before "-epoch:"
        match = re.match(r"^(.+?)-\d+:", nevra_string)
        if match:
            return match.group(1)

    # No epoch: name-version-release.arch
    # Just take the first segment before the first hyphen
    return nevra_string.split("-")[0]


def extract_module_packages(modules_yaml_path):  # noqa: C901
    """Parse modulemd YAML and return module -> packages mapping."""

    module_packages = defaultdict(lambda: defaultdict(set))
    module_count = 0
    skipped_count = 0

    print(f"Parsing {modules_yaml_path}...")

    try:
        with open(modules_yaml_path, "r") as f:
            # modules.yaml contains multiple YAML documents separated by "---"
            documents = yaml.safe_load_all(f)

            for doc in documents:
                if not doc:
                    continue

                # Module documents have document: modulemd
                if doc.get("document") != "modulemd":
                    continue

                # Skip obsolete modulemd versions
                if doc.get("version", 0) < 2:
                    continue

                data = doc.get("data", {})
                module_name = data.get("name")
                stream = data.get("stream")

                if not module_name or not stream:
                    continue

                # Extract package names from artifacts
                artifacts = data.get("artifacts", {})
                rpms = artifacts.get("rpms", [])

                if not rpms:
                    skipped_count += 1
                    continue

                package_names = set()
                for rpm_nevra in rpms:
                    # Skip debuginfo and debugsource packages
                    if "debuginfo" in rpm_nevra or "debugsource" in rpm_nevra:
                        continue

                    # Only process x86_64 and src packages (skip i686, etc.)
                    if not (".x86_64" in rpm_nevra or ".src" in rpm_nevra or ".noarch" in rpm_nevra):
                        continue

                    pkg_name = parse_nevra(rpm_nevra)
                    package_names.add(pkg_name)

                if package_names:
                    # Detect OS major version from the NEVRA release string
                    # Look for .el8 or .el9 or module+el8 patterns
                    os_major = None
                    for rpm in rpms[:5]:  # Check first few packages
                        if ".el8" in rpm or "module+el8" in rpm or "module_el8" in rpm:
                            os_major = 8
                            break
                        elif ".el9" in rpm or "module+el9" in rpm or "module_el9" in rpm:
                            os_major = 9
                            break
                        elif ".el10" in rpm or "module+el10" in rpm or "module_el10" in rpm:
                            os_major = 10
                            break

                    if os_major:
                        key = (module_name, os_major, str(stream))
                        module_packages[key] = package_names
                        module_count += 1

    except FileNotFoundError:
        print(f"ERROR: File not found: {modules_yaml_path}", file=sys.stderr)
        print("Run ./download_modulemd.sh first to download module metadata", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR parsing {modules_yaml_path}: {e}", file=sys.stderr)
        return None

    print(f"  ✓ Processed {module_count} modules, skipped {skipped_count} without artifacts")
    return dict(module_packages)


def load_tracked_modules():
    """Load the list of modules we actually track from modules.py."""
    from roadmap.data.modules import APP_STREAM_MODULES

    tracked = set()
    for module in APP_STREAM_MODULES:
        tracked.add((module.name, module.os_major, module.stream))

    print(f"\nTracked modules in codebase: {len(tracked)}")
    return tracked


def generate_module_packages_file(all_packages, output_path):
    """Generate the module_packages.py file."""

    print(f"\nGenerating {output_path}...")

    # Sort by (os_major, module_name, stream) for readability
    sorted_items = sorted(all_packages.items(), key=lambda x: (x[0][1], x[0][0], x[0][2]))

    with open(output_path, "w") as f:
        f.write('"""\n')
        f.write("AppStream Module to Package Mappings\n")
        f.write("\n")
        f.write("This file maps (module_name, os_major, stream) -> set of package names.\n")
        f.write("Used to determine if an enabled module actually has packages installed.\n")
        f.write("\n")
        f.write(
            f"Auto-generated by scripts/generate_module_packages.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write('"""\n\n')

        f.write("MODULE_PACKAGES = {\n")

        current_os_major = None
        for (module_name, os_major, stream), packages in sorted_items:
            # Add a blank line and comment for each OS major version
            if current_os_major != os_major:
                if current_os_major is not None:
                    f.write("\n")
                f.write(f"    # RHEL {os_major} Modules\n")
                current_os_major = os_major

            # Format the package set nicely
            sorted_packages = sorted(packages)

            # If packages fit on one line (< 100 chars), use single line
            packages_str = ", ".join(f'"{pkg}"' for pkg in sorted_packages)
            if len(packages_str) < 80:
                f.write(f'    ("{module_name}", {os_major}, "{stream}"): {{{packages_str}}},\n')
            else:
                # Multi-line format for readability
                f.write(f'    ("{module_name}", {os_major}, "{stream}"): {{\n')
                for i, pkg in enumerate(sorted_packages):
                    if i == len(sorted_packages) - 1:
                        f.write(f'        "{pkg}"\n')
                    else:
                        f.write(f'        "{pkg}",\n')
                f.write("    },\n")

        f.write("}\n")

    print(f"  ✓ Generated {len(all_packages)} module mappings")


def main():
    """Main execution."""
    print("=" * 60)
    print("Module Packages Data Generator")
    print("=" * 60)

    # Setup paths
    repo_root = Path(__file__).parent.parent
    modulemd_dir = repo_root / "modulemd_data"
    output_file = repo_root / "src" / "roadmap" / "data" / "module_packages.py"

    # Check if modulemd directory exists
    if not modulemd_dir.exists():
        print(f"\nERROR: Directory not found: {modulemd_dir}", file=sys.stderr)
        print("\nRun ./download_modulemd.sh first to download module metadata", file=sys.stderr)
        return 1

    # Parse YAML files
    all_packages = {}

    for version in [8, 9, 10]:
        yaml_path = modulemd_dir / f"modules-{version}.yaml"
        if yaml_path.exists():
            packages = extract_module_packages(yaml_path)
            if packages:
                all_packages.update(packages)
        else:
            print(f"Warning: {yaml_path} not found, skipping RHEL {version}")

    if not all_packages:
        print("\nERROR: No module data extracted!", file=sys.stderr)
        return 1

    print(f"\nTotal modules extracted: {len(all_packages)}")

    # Load tracked modules to see coverage
    try:
        tracked_modules = load_tracked_modules()

        # Find intersection
        extracted_keys = set(all_packages.keys())
        covered = tracked_modules & extracted_keys
        missing = tracked_modules - extracted_keys

        print(f"Coverage: {len(covered)}/{len(tracked_modules)} tracked modules have package data")

        if missing:
            print(f"\nWarning: {len(missing)} tracked modules missing from modulemd:")
            for module_name, os_major, stream in sorted(missing)[:10]:
                print(f"  - {module_name}:{stream} (RHEL {os_major})")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")

    except ImportError:
        print("\nNote: Could not import roadmap.data.modules (not in PYTHONPATH)")
        print("Proceeding with all extracted modules...")

    # Generate output file
    generate_module_packages_file(all_packages, output_file)

    print(f"\n{'=' * 60}")
    print(f"✓ Success! Generated {output_file}")
    print(f"{'=' * 60}")

    # Print some example entries for verification
    print("\nExample entries:")
    for i, ((module_name, os_major, stream), packages) in enumerate(sorted(all_packages.items())[:5]):
        print(f"  {module_name}:{stream} (RHEL {os_major}) -> {len(packages)} packages")
        print(f"    Example packages: {', '.join(sorted(packages)[:3])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
