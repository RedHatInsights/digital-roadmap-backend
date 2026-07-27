from collections import defaultdict

from .app_streams import AppStreamEntity
from .app_streams import AppStreamType
from .module_packages import MODULE_PACKAGES as MODULE_PACKAGES
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
        for stream in data
        if stream.application_stream_type in (AppStreamType.stream, AppStreamType.full)
    )  # fmt: off

    return app_streams


def _shared_package_names(module_packages: dict[tuple[str, int, str], set[str]]) -> dict[int, set[str]]:
    """Return, per RHEL major version, package names referenced by more than one module.

    These are ambiguous signals (e.g. jansi and hawtjni-runtime appear in both
    scala and maven) and cannot be trusted on their own to verify a module is
    in use. Packages unique to a single module are trustworthy evidence.
    """
    owners_by_os_major: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for (module_name, os_major, _stream), pkgs in module_packages.items():
        for pkg in pkgs:
            owners_by_os_major[os_major][pkg].add(module_name)

    return {
        os_major: {pkg for pkg, modules in owners.items() if len(modules) > 1}
        for os_major, owners in owners_by_os_major.items()
    }


APP_STREAM_MODULES_BY_KEY = {(asm.name, asm.os_major, asm.stream): asm for asm in APP_STREAM_MODULES}
OS_MAJORS_BY_APP_NAME = _os_majors_by_app_name()
APP_STREAM_MODULES_PACKAGES = _modules_packages()
APP_STREAMS = _only_app_streams(APP_STREAM_MODULES_PACKAGES)
SHARED_PACKAGE_NAMES_BY_OS_MAJOR = _shared_package_names(MODULE_PACKAGES)
