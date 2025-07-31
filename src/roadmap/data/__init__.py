from collections import defaultdict
from datetime import date

from roadmap.models import _calculate_support_status

from .app_streams import AppStream
from .app_streams import AppStreamType
from .modules import APP_STREAM_MODULES
from .packages import APP_STREAM_PACKAGES


def _os_majors_by_app_name():
    result = defaultdict(set)
    for asm in APP_STREAM_MODULES:
        result[asm.name].add(asm.os_major)

    return dict(result)


def _only_app_streams(data) -> set[AppStream]:
    app_streams = set(
        AppStream(
            display_name=n.display_name,
            os_major=n.os_major,
            os_minor=n.os_minor,
            start_date=n.start_date,
            end_date=n.end_date,
            application_stream_type=n.application_stream_type,
            application_stream_name=n.application_stream_name,
            support_status=_calculate_support_status(n.start_date, n.end_date, date.today(), 6),
        )
        for n in APP_STREAM_MODULES_PACKAGES
        if n.application_stream_type in (AppStreamType.stream, AppStreamType.full)
    )

    return app_streams


APP_STREAM_MODULES_BY_KEY = {(asm.name, asm.os_major, asm.stream): asm for asm in APP_STREAM_MODULES}
OS_MAJORS_BY_APP_NAME = _os_majors_by_app_name()
APP_STREAM_MODULES_PACKAGES = [
    *APP_STREAM_MODULES,
    *[package for os_packages in APP_STREAM_PACKAGES.values() for package in os_packages.values()],
]
APP_STREAMS = _only_app_streams(APP_STREAM_MODULES_PACKAGES)
