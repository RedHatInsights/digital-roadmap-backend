from collections import defaultdict

from .app_streams import AppStreamEntity
from .app_streams import AppStreamType
from .modules import APP_STREAM_MODULES
from .packages import APP_STREAM_PACKAGES


def _os_majors_by_app_name():
    result = defaultdict(set)
    for asm in APP_STREAM_MODULES:
        result[asm.name].add(asm.os_major)

    return dict(result)


def _modules_packages():
    packages = [
        package
        for os_packages in APP_STREAM_PACKAGES.values()
        for package in os_packages.values()
    ]  # fmt: skip

    return APP_STREAM_MODULES + packages


def _only_app_streams(data) -> set[AppStreamEntity]:
    app_streams = set(
        stream
        for stream in APP_STREAM_MODULES_PACKAGES
        if stream.application_stream_type in (AppStreamType.stream, AppStreamType.full)
    )

    return app_streams


APP_STREAM_MODULES_BY_KEY = {(asm.name, asm.os_major, asm.stream): asm for asm in APP_STREAM_MODULES}
OS_MAJORS_BY_APP_NAME = _os_majors_by_app_name()
APP_STREAM_MODULES_PACKAGES = _modules_packages()
APP_STREAMS = _only_app_streams(APP_STREAM_MODULES_PACKAGES)
