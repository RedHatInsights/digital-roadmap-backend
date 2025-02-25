#!/usr/bin/env python

import json
import sys
import uuid

from pathlib import Path


def main():
    file = Path(sys.argv[1]).resolve()
    data = json.loads(file.read_text())

    new = {key: data[key] for key in set(data).difference(["results"])}

    # Only keep the minimum data
    keys_to_keep = {"system_profile", "id"}
    new["results"] = [
        {key: value}
        for result in data["results"]
        for key, value in result.items() if key in keys_to_keep
    ]  # fmt: skip

    # Replace IDs
    for result in new["results"]:
        result["id"] = str(uuid.uuid4())

    file.with_suffix(".scrubbed.json").write_text(json.dumps(new, indent=2) + "\n")


if __name__ == "__main__":
    main()
