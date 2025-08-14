#!/usr/bin/env python

import datetime
import pathlib


today = datetime.date.today()
count = 1
release_file = pathlib.Path(__file__).parent / ".release"
try:
    current_release = release_file.read_text()
except FileNotFoundError:
    pass
else:
    date, count = current_release.rsplit("-", 1)
    date = datetime.date.fromisoformat(date)
    count = int(count)
    if date == today:
        count += 1
    else:
        count = 1
finally:
    release = f"{today}-{count:02}\n"
    release_file.write_text(release)
    print(release[:-1])
