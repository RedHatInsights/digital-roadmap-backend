from collections import defaultdict

from .modules import APP_STREAM_MODULES
from .packages import APP_STREAM_PACKAGES


def _os_majors_by_app_name():
    result = defaultdict(set)
    for asm in APP_STREAM_MODULES:
        result[asm.name].add(asm.os_major)

    return dict(result)


APP_STREAM_MODULES_BY_KEY = {(asm.name, asm.os_major, asm.stream): asm for asm in APP_STREAM_MODULES}
OS_MAJORS_BY_APP_NAME = _os_majors_by_app_name()
APP_STREAM_MODULES_PACKAGES = [*APP_STREAM_MODULES, *APP_STREAM_PACKAGES.values()]
