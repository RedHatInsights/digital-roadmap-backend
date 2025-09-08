#!/usr/bin/env python


import dataclasses
import datetime
import subprocess
import sys
import textwrap


@dataclasses.dataclass
class Tagger:
    branch: str

    @property
    def tags(self) -> list[str]:
        result = subprocess.run(
            ["git", "tag", "--list", "--format=%(refname:short).%(objectname)", "--sort=-refname"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().splitlines()

    @property
    def latest_tag(self) -> str:
        return self.tags[0]

    @property
    def latest_commit(self) -> str:
        result = subprocess.run(["git", "rev-parse", self.branch], capture_output=True, text=True)
        return result.stdout.rstrip()

    def tag_release(self):
        today = datetime.date.today()
        latest_tag_date, count, commit = self.latest_tag.rsplit(".")
        latest_tag_date = datetime.date.fromisoformat(latest_tag_date)
        count = int(count)

        if latest_tag_date == today:
            count += 1

        for idx, tag in enumerate(self.tags):
            if self.latest_commit in tag:
                break
        else:
            release_tag = f"{today}.{count:02}"
            subprocess.run(["git", "tag", release_tag, self.latest_commit])
            print(f"Tagged {self.latest_commit} with {release_tag}.")
            return

        print(f"Commit {self.latest_commit:7} is already tagged.")
        tags = self.tags[:]
        tags[idx] += " <--"
        sys.exit(textwrap.indent("\n".join(tags), " " * 4))


if __name__ == "__main__":
    tagger = Tagger("main")
    tagger.tag_release()
