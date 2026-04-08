"""Shared constants and factory functions for notificator tests."""

from datetime import datetime
from datetime import UTC
from uuid import UUID

from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.data.app_streams import AppStreamType
from roadmap.models import LifecycleType
from roadmap.models import System
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import AppStreamKey


FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")
FIXED_DATETIME = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
FIXED_TIMESTAMP = "2026-03-15T12:00:00Z"
ORG_ID = 1234

EMPTY_RHEL_SECTIONS = {
    "rhel_retired": {"rhel_versions_count": 0, "systems_count": 0},
    "rhel_near_retirement": {"rhel_versions_count": 0, "systems_count": 0},
}
EMPTY_APPSTREAM_SECTIONS = {
    "appstream_retired": {},
    "appstream_near_retirement": {},
}


def make_system_info(n, os_major=9):
    """Create a SystemInfo with a deterministic UUID derived from *n*."""
    return SystemInfo(id=UUID(int=n), display_name=f"host-{n}", os_major=os_major, os_minor=1)


def make_appstream_key(name, display_name, status, os_major):
    """Build an AppStreamKey with a specific support_status, bypassing validators."""
    entity = AppStreamEntity.model_construct(
        name=name,
        display_name=display_name,
        application_stream_name=name,
        application_stream_type=AppStreamType.stream,
        stream="1.0",
        impl=AppStreamImplementation.module,
        support_status=status,
        os_major=os_major,
        os_minor=None,
        start_date=None,
        end_date=None,
        initial_product_version=None,
        lifecycle=None,
        rolling=False,
    )
    return AppStreamKey.model_construct(name=name, app_stream_entity=entity)


def make_system(name, status, count, major, minor=None):
    """Build a System with a specific support_status, bypassing validators."""
    display_name = f"{name} {major}" + (f".{minor}" if minor is not None else "")
    return System.model_construct(
        name=name,
        display_name=display_name,
        major=major,
        minor=minor,
        lifecycle_type=LifecycleType.mainline,
        count=count,
        start_date=None,
        end_date=None,
        support_status=status,
        related=False,
        systems_detail=set(),
        systems=set(),
    )
