from datetime import date

from roadmap.models import SupportStatus


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
