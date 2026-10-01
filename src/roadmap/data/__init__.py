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


def app_stream_inventory_candidates(name: str | None, os_major: int | None) -> tuple[set[str], set[str]]:
    """Return inventory names that can produce a matching App Stream.

    The returned names mirror the inventory evidence consumed by the App Stream
    matcher: module names come from the canonical module index and package names
    come from the keys used by ``app_stream_from_package``.  The result is a
    conservative candidate set for HBI filtering; it is not an exact match.
    """
    modules = [
        module for module in APP_STREAM_MODULES_BY_KEY.values() if os_major is None or module.os_major == os_major
    ]
    packages = [
        (package_name, package)
        for major, package_map in APP_STREAM_PACKAGES.items()
        if os_major is None or major == os_major
        for package_name, package in package_map.items()
    ]

    if name is not None:
        module_name_match = any(module.name == name for module in modules)
        modules = [module for module in modules if module.name == name or module.application_stream_name == name]

        if module_name_match:
            # A module name identifies a family of streams, while package-only
            # inventory evidence can use a different package name (for example
            # ``npm`` is mapped to the Node.js family). Include every package
            # entity in the same display-name family so missing module profiles
            # cannot make the HBI pre-filter drop a real package match.
            families = {module.application_stream_name.rstrip("0123456789. ").casefold() for module in modules}
            packages = [
                (package_name, package)
                for package_name, package in packages
                if package_name == name or package.application_stream_name.rstrip("0123456789. ").casefold() in families
            ]
        else:
            packages = [
                (package_name, package)
                for package_name, package in packages
                if package_name == name or package.application_stream_name == name
            ]

    return {module.name for module in modules}, {package_name for package_name, _ in packages}
