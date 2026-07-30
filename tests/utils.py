from datetime import date
from uuid import uuid4

from roadmap.models import SupportStatus


class MockAsyncMappings:
    """Simulates SQLAlchemy's async .yield_per().mappings() chain for testing."""

    def __init__(self, rows):
        self._rows = rows

    def yield_per(self, n):
        return self

    def mappings(self):
        return self

    def __aiter__(self):
        self._iter = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def make_host_rows(count, *, os_major=9, os_minor=1, packages=None):
    """Generate minimal valid host inventory rows for testing."""
    return [
        {
            "id": uuid4(),
            "display_name": f"host-{i}",
            "os_name": "RHEL",
            "os_major": os_major,
            "os_minor": os_minor,
            "os_release": f"{os_major}.{os_minor}",
            "dnf_modules": [],
            "packages": packages or [],
            "products": [{}],
        }
        for i in range(count)
    ]


SUPPORT_STATUS_TEST_CASES = (
    # OK situation, stream supported
    (
        date(2025, 3, 27),
        date(2020, 1, 1),
        date(2027, 12, 31),
        SupportStatus.supported,
    ),
    # Stream retired
    (
        date(2028, 1, 1),
        date(2020, 1, 1),
        date(2027, 12, 31),
        SupportStatus.retired,
    ),
    # Stream not yet started
    (
        date(2019, 12, 31),
        date(2020, 1, 1),
        date(2027, 12, 31),
        SupportStatus.upcoming,
    ),
    # Stream has no end date
    (
        date(2025, 3, 27),
        date(2020, 1, 1),
        None,
        SupportStatus.unknown,
    ),
    # Stream has no start date
    (
        date(2025, 3, 27),
        None,
        date(2027, 12, 31),
        SupportStatus.supported,
    ),
    # Stream has no start or end date
    (
        date(2025, 3, 27),
        None,
        None,
        SupportStatus.unknown,
    ),
)
