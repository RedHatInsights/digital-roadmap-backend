#!/usr/bin/env python3

import argparse
import gzip
import json
import uuid

from collections.abc import Iterator
from pathlib import Path


CHUNK_SIZE = 1024 * 1024


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate hosts from HBI system profiles.")
    parser.add_argument("--input", required=True, type=Path, help="HBI hosts JSON file")
    parser.add_argument("--output", required=True, type=Path, help="Generated JSON file")
    parser.add_argument("--count", required=True, type=positive_int, help="Number of hosts to generate")
    return parser.parse_args()


def iter_hosts(path: Path) -> Iterator[dict]:  # noqa: C901
    decoder = json.JSONDecoder()
    buffer = ""
    position = 0
    state = "array_start"
    eof = False

    source_file = gzip.open(path, mode="rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")
    with source_file as source:
        while True:
            while position < len(buffer) and buffer[position].isspace():
                position += 1

            if state == "done":
                if position < len(buffer):
                    raise ValueError("unexpected data after the JSON array")
                chunk = source.read(CHUNK_SIZE)
                if chunk:
                    buffer = chunk
                    position = 0
                    continue
                return

            if position == len(buffer):
                if eof:
                    raise ValueError("unexpected end of JSON input")
                buffer = buffer[position:] + source.read(CHUNK_SIZE)
                position = 0
                if not buffer:
                    eof = True
                continue

            if state == "array_start":
                if buffer[position] != "[":
                    raise ValueError("input must be a JSON array")
                position += 1
                state = "value_or_end"
                continue

            if state == "comma_or_end":
                if buffer[position] == ",":
                    position += 1
                    state = "value"
                    continue
                if buffer[position] == "]":
                    position += 1
                    state = "done"
                    continue
                raise ValueError("expected ',' or ']' after a host")

            if state == "value_or_end" and buffer[position] == "]":
                position += 1
                state = "done"
                continue

            try:
                host, position = decoder.raw_decode(buffer, position)
            except json.JSONDecodeError as error:
                if eof:
                    raise ValueError(f"invalid JSON: {error}") from error
                chunk = source.read(CHUNK_SIZE)
                buffer = buffer[position:] + chunk
                position = 0
                if not chunk:
                    eof = True
                continue

            if not isinstance(host, dict):
                raise ValueError("each host must be a JSON object")
            yield host
            state = "comma_or_end"


def iter_hosts_with_profiles(path: Path) -> Iterator[dict]:
    for host in iter_hosts(path):
        system_profile = host.get("system_profile")
        if isinstance(system_profile, dict) and system_profile:
            yield host


def count_hosts(path: Path) -> int:
    count = sum(1 for _ in iter_hosts_with_profiles(path))
    if count == 0:
        raise ValueError("input contains no hosts with system profiles")
    return count


def generate_hosts(input_path: Path, output_path: Path, count: int) -> None:
    source_count = count_hosts(input_path)
    copies_per_host, hosts_with_extra_copy = divmod(count, source_count)
    generated = 0

    print(f"Found {source_count:,} source hosts. Generating {count:,} hosts...")
    with output_path.open("w", encoding="utf-8") as output:
        output.write("[\n")
        for source_index, source_host in enumerate(iter_hosts_with_profiles(input_path)):
            copies = copies_per_host + (source_index < hosts_with_extra_copy)
            for _ in range(copies):
                host_id = str(uuid.uuid4())
                host = {
                    "id": host_id,
                    "display_name": host_id.replace("-", ""),
                    "system_profile": source_host["system_profile"],
                }
                if generated:
                    output.write(",\n")
                json.dump(host, output, ensure_ascii=False, separators=(",", ":"))
                generated += 1
                if generated % 10_000 == 0:
                    print(f"Generated {generated:,}/{count:,} hosts")
            if generated == count:
                break
        output.write("\n]\n")

    print(f"Wrote {generated:,} hosts to {output_path}")


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()

    if input_path == output_path:
        raise SystemExit("Input and output paths must be different.")
    if not input_path.is_file():
        raise SystemExit(f"Input file does not exist: {input_path}")
    if not output_path.parent.is_dir():
        raise SystemExit(f"Output directory does not exist: {output_path.parent}")

    try:
        generate_hosts(input_path, output_path, args.count)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error


if __name__ == "__main__":
    main()
