from collections import defaultdict

from .modules import APP_STREAM_MODULES
from .packages import APP_STREAM_PACKAGES


APP_STREAM_MODULES_BY_KEY = {(asm.name, asm.os_major, asm.stream): asm for asm in APP_STREAM_MODULES}

OS_MAJORS_BY_APP_NAME = defaultdict(set)
for asm in APP_STREAM_MODULES:
    OS_MAJORS_BY_APP_NAME[asm.name].add(asm.os_major)
OS_MAJORS_BY_APP_NAME = dict(OS_MAJORS_BY_APP_NAME)

APP_STREAM_MODULES_PACKAGES = [*APP_STREAM_MODULES, *APP_STREAM_PACKAGES.values()]
