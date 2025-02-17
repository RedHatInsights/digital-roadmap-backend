#!/usr/bin/env python

import json
import sys

from pathlib import Path


def main():
    file = Path(sys.argv[1]).resolve()
    data = json.loads(file.read_text())

    new = {key: data[key] for key in set(data).difference(["results"])}
    new["results"] = [{"system_profile": result["system_profile"]} for result in data["results"]]

    file.with_suffix(".scrubbed.json").write_text(json.dumps(new, indent=2) + "\n")


if __name__ == "__main__":
    main()
