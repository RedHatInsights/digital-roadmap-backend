#!/bin/bash
# Script to download modulemd files from RHEL-compatible sources
# and strip them to minimal format for generate_module_packages.py
#
# Usage:
#   ./scripts/download_modulemd.sh
#
# Output:
#   modulemd_data/modules-8.yaml  - Minimal modulemd for RHEL 8
#   modulemd_data/modules-9.yaml  - Minimal modulemd for RHEL 9
#
# Sources:
#   - RHEL 8: Rocky Linux 8 (latest, includes all RHEL 8.x modules)
#   - RHEL 9: CentOS Stream 9 (active upstream)
#
# The script automatically strips downloaded files to minimal format,
# keeping only: document, version, data.name, data.stream, data.artifacts.rpms
# This reduces file size by ~50% and eliminates YAML formatting issues.

set -e

WORKDIR="modulemd_data"
mkdir -p "$WORKDIR"

# Function to download modules.yaml for a given version
download_modules() {
    local version=$1
    local repo_name repo_url

    case "$version" in
        8)
            repo_name="Rocky Linux 8 (Latest)"
            repo_url="https://download.rockylinux.org/pub/rocky/8/AppStream/x86_64/os/repodata"
            ;;
        9)
            repo_name="CentOS Stream 9"
            repo_url="https://mirror.stream.centos.org/9-stream/AppStream/x86_64/os/repodata"
            ;;
        *)
            echo "Error: Unsupported version $version"
            return 1
            ;;
    esac

    echo "Downloading modulemd for $repo_name..."

    # Get repomd.xml to find modules file
    repomd_xml="$WORKDIR/repomd-${version}.xml"
    echo "  Fetching repomd.xml..."
    if ! curl -f -s "${repo_url}/repomd.xml" -o "$repomd_xml"; then
        echo "  ✗ Error: Could not download repomd.xml from $repo_url"
        return 1
    fi

    # Extract modules.yaml location from repomd.xml
    modules_file=$(grep -A 3 'type="modules"' "$repomd_xml" | \
                   grep -oP '(?<=location href=")[^"]+' | head -1)

    if [ -z "$modules_file" ]; then
        echo "  ✗ Error: Could not find modules file in repomd.xml"
        return 1
    fi

    echo "  Downloading ${modules_file}..."

    # Determine compression format from filename
    if [[ "$modules_file" == *.gz ]]; then
        compressed_file="$WORKDIR/modules-${version}.yaml.gz"
        decompress_cmd="gunzip -f"
    elif [[ "$modules_file" == *.xz ]]; then
        compressed_file="$WORKDIR/modules-${version}.yaml.xz"
        decompress_cmd="xz -d"
    else
        compressed_file="$WORKDIR/modules-${version}.yaml"
        decompress_cmd=""
    fi

    # Download the modules file
    # Remove the repodata/ prefix from modules_file if present (it's already in repo_url)
    modules_file_basename=$(basename "$modules_file")

    if ! curl -f -s "${repo_url}/${modules_file_basename}" -o "$compressed_file"; then
        echo "  ✗ Error: Could not download modules file"
        return 1
    fi

    # Decompress if needed
    if [ -n "$decompress_cmd" ]; then
        echo "  Decompressing..."
        $decompress_cmd "$compressed_file"
    fi

    # Verify the file exists and has content
    if [ ! -s "$WORKDIR/modules-${version}.yaml" ]; then
        echo "  ✗ Error: modules-${version}.yaml is empty or missing"
        return 1
    fi

    local full_size=$(du -h "$WORKDIR/modules-${version}.yaml" | cut -f1)
    echo "  ✓ Downloaded full modulemd file ($full_size)"

    # Strip to minimal format (keep only fields needed for generate_module_packages.py)
    echo "  Stripping to minimal format..."
    local input_file="$WORKDIR/modules-${version}.yaml"
    local temp_file="$WORKDIR/modules-${version}.yaml.tmp"

    python3 << PYTHON_EOF
import sys
import yaml

try:
    with open('${input_file}') as f:
        docs = list(yaml.safe_load_all(f))

    minimal_docs = []
    for doc in docs:
        if not doc:
            continue

        if doc.get('document') == 'modulemd':
            # Keep only essential fields
            minimal = {
                'document': 'modulemd',
                'version': doc.get('version'),
                'data': {
                    'name': doc['data']['name'],
                    'stream': doc['data']['stream'],
                    'artifacts': {
                        'rpms': doc['data'].get('artifacts', {}).get('rpms', [])
                    }
                }
            }
            minimal_docs.append(minimal)
        elif doc.get('document') == 'modulemd-defaults':
            # Keep defaults as-is
            minimal_docs.append(doc)

    with open('${temp_file}', 'w') as f:
        yaml.dump_all(minimal_docs, f, default_flow_style=False, sort_keys=False)

    sys.exit(0)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF

    if [ $? -eq 0 ]; then
        mv "$temp_file" "$input_file"
        local minimal_size=$(du -h "$WORKDIR/modules-${version}.yaml" | cut -f1)
        echo "  ✓ Stripped to minimal format: $full_size → $minimal_size"
    else
        echo "  ✗ Warning: Failed to create minimal file, keeping full version"
        rm -f "$temp_file"
    fi
}

echo "========================================"
echo "  ModuleMD Metadata Downloader"
echo "========================================"
echo ""

# Download for RHEL 8 and 9 equivalents
download_modules 8 || echo "Warning: Failed to download RHEL 8 modules"
echo ""
download_modules 9 || echo "Warning: Failed to download RHEL 9 modules"

echo ""
echo "========================================"
echo "Done! Module metadata saved in $WORKDIR/"
echo ""
echo "Next step:"
echo "  python scripts/generate_module_packages.py"
echo "========================================"
