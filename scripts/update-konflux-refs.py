#!/usr/bin/env python
import argparse
import json
import math
import sys
import textwrap
import typing as t
import urllib.request

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
from itertools import islice
from operator import itemgetter
from pathlib import Path


try:
    import argcomplete  # pyright: ignore[reportMissingImports]
except ImportError:
    argcomplete = None


def _batched(iterable: t.Iterable, batch_size: int) -> t.Iterable[tuple[t.Any, ...]]:
    """Yield batches based on chunk size.

    Roughly equivalent to itertools.batched in Python >= 3.12.
    https://docs.python.org/3/library/itertools.html#itertools.batched
    """

    if batch_size < 1:
        raise ValueError("Batch size must be at least 1.")

    iterator = iter(iterable)
    while batch := tuple(islice(iterator, batch_size)):
        yield batch


try:
    from itertools import batched
except ImportError:
    batched = _batched


QUAYIO = "quay.io/"


class Color(StrEnum):
    reset = "\033[0m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"
    br_red = "\033[91m"
    br_green = "\033[92m"
    br_yellow = "\033[93m"
    br_blue = "\033[94m"
    br_magenta = "\033[95m"
    br_cyan = "\033[96m"
    br_white = "\033[97m"


def _positive_int(value):
    validated = int(value)
    if validated < 1:
        raise ValueError("Must be positive")

    return validated


def parse_args():
    description = """
    Update container refs in a file or list all tags.

    By default, a new file is created with an '_updated' suffix. To make changes
    to the original file, use the '--overwrite' argument.

    Tags are sorted by version and date in descending order.

    Long tags are filetered out by default. This can be
    adjusted with the '--tag-length' argument.

    This is specifically for handling quay.io/konflux-ci images. It will not
    work with other container registries or images.
    """
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(description),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.register("type", "positive integer", _positive_int)
    parser.add_argument("--file", "-f", required=False, type=Path)
    parser.add_argument("--image", "-i", required=False, help="Print out list of tags for a given image")
    parser.add_argument("--overwrite", "-o", action="store_true")
    parser.add_argument("--tag-length", "-l", default=4, type=int, help="Tags greater than this length will be omitted")
    parser.add_argument("--max-count", "-m", help="Maximum number of image tags to gather", type=int, default=50)
    parser.add_argument("--workers", "-t", help="Number of concurrent workers", type="positive integer", default=16)

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser.parse_args()


def filter_tags(
    tags: list[dict[str, t.Any]],
    key: list[str] | None = None,
    reverse: bool = True,
    max_tag_length: int = 128,
) -> list[dict[str, t.Any]]:
    # operator.itemgetter will return a tuple of items if passed a list of items to get.
    # This means the value used to sort will look like ('0.7', 1765550189).
    key = key or ["name", "start_ts"]
    exclude = {"unknown"}
    return sorted(
        (item for item in tags if len(item["name"]) < max_tag_length and item["name"] not in exclude),
        key=itemgetter(*key),
        reverse=reverse,
    )


def get_tags(repository: str, max_count: int = 100) -> list[dict[str, t.Any]]:
    if not repository:
        sys.exit("Missing repo")

    if repository.startswith(QUAYIO):
        repository = repository.lstrip(QUAYIO)

    quay_api_url = f"https://quay.io/api/v1/repository/{repository}/tag/"

    has_additional = True
    all_tags = []
    page = 1
    while has_additional:
        try:
            with urllib.request.urlopen(f"{quay_api_url}?page={page}") as response:
                data = response.read()
        except urllib.request.HTTPError as err:
            sys.exit(f"Error trying to get tags for {repository}: {err}")

        data = json.loads(data)
        page = data.get("page", 1)
        tags = data.get("tags", [])
        all_tags.extend(tags)

        # Conditions that stop additional requests
        has_additional = data.get("has_additional", False)

        if len(all_tags) >= max_count:
            break

        page += 1

    return all_tags


def get_latest_tag(repository: str, max_tag_length: int):
    tags = get_tags(repository)
    return filter_tags(tags, max_tag_length=max_tag_length)[0]


def get_container_image_names(repository: str, tags: list[dict[str, t.Any]]) -> list[str]:
    # Get the padding size in order to make the name@digest section a consistent width
    if not tags:
        return []

    longest_name = max(len(tag["name"]) for tag in tags)
    longest_digest = max(len(tag["manifest_digest"]) for tag in tags)
    padding = longest_name + longest_digest

    return [
        f"{Color.yellow}{repository}{Color.reset}"
        f":{Color.blue}{tag['name']}{Color.reset}"
        f"@{Color.magenta}{tag['manifest_digest']:{padding - len(tag['name'])}}{Color.reset}"
        f"{tag['last_modified']:>33}"
        for tag in tags
    ]


def parse_container_image(line) -> tuple[str, str, str]:
    line = line.strip()
    try:
        # Remove the leading prefix if it exists and anything before it
        line = line[line.index(QUAYIO) :]
    except IndexError:
        pass

    # The image could only have the digest and not the tag
    #   quay.io/konflux-ci/tekton-catalog/task-push-dockerfile@sha256:389dc0f7bb175b9ca04e79ee67352fedd62fff8b1d196029534cd5638c73a0fc
    #   quay.io/konflux-ci/tekton-catalog/task-git-clone:0.1@sha256:d091a9e19567a4cbdc5acd57903c71ba71dc51d749a4ba7477e689608851e981',
    #   quay.io/konflux-ci/tekton-catalog/task-git-clone:0.1

    image, _, digest = line.partition("@")
    image, _, tag = image.partition(":")

    return image, tag, digest


def array_split(lines: list[str], number: int) -> t.Iterable[tuple[str, ...]]:
    if number < 1:
        raise ValueError("number must be at least 1.")

    chunk_size = math.ceil(len(lines) / number)
    return batched(lines, chunk_size)


def process_chunk(data: t.Iterable[str], max_tag_length: int) -> list[str]:
    updated = []
    for line in data:
        if "quay.io/konflux-ci" in line:
            image, tag, digest = parse_container_image(line)
            latest_tag = get_latest_tag(image.lstrip(QUAYIO), max_tag_length=max_tag_length)

            print(f"Updating {image}", flush=True)

            tag = f":{tag}" if tag else ""
            digest = f"@{digest}" if digest else ""
            current_image = f"{image}{tag}{digest}"

            new_tag = f":{latest_tag['name']}" if tag else ""
            new_digest = f"@{latest_tag['manifest_digest']}" if digest else ""
            new_image = f"{image}{new_tag}{new_digest}"
            line = line.replace(current_image, new_image)

        updated.append(line)

    return updated


def main():
    args = parse_args()

    file = args.file
    container_image: str = args.image
    overwrite = args.overwrite
    max_tag_length = args.tag_length
    max_count = args.max_count
    workers = args.workers

    if file:
        file_content = file.read_text().splitlines()
        output_file = file.with_name(f"{file.stem}_updated{file.suffix}")
        if overwrite:
            output_file = file

        chunks = array_split(file_content, workers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Use future objects as a key to preserve submission order.
            future_chunks = {executor.submit(process_chunk, chunk, max_tag_length): [] for chunk in chunks}
            for future in as_completed(future_chunks):
                try:
                    future_chunks[future] = future.result()
                except Exception as exc:
                    print(f"Problem getting data: {exc}.")

        # Reassemble the lines in the order they were submitted.
        updated = [n for lines in future_chunks.values() for n in lines]
        output_file.write_text("\n".join(updated) + "\n")
        sys.exit()

    tags = get_tags(container_image, max_count)
    filtered = filter_tags(tags, max_tag_length=max_tag_length)
    images = get_container_image_names(container_image, filtered)

    print(f"{container_image}:")
    print(textwrap.indent("\n".join(images), " " * 4))


if __name__ == "__main__":
    main()
