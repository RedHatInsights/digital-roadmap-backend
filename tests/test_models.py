from datetime import date

import pytest

from roadmap.models import _get_rhel_display_name
from roadmap.models import LifecycleType
from roadmap.models import SupportStatus
from roadmap.models import System


@pytest.mark.parametrize(
    ("current_date", "system_start", "system_end", "status"),
    (
        (
            # OK situation, stream supported
            date(2025, 3, 27),
            date(2020, 1, 1),
            date(2027, 12, 31),
            SupportStatus.supported,
        ),
        # Support ends within 6 months (180 days)
        (
            date(2027, 6, 15),
            date(2020, 1, 1),
            date(2027, 12, 1),
            SupportStatus.six_months,
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
    ),
)
def test_calculate_support_status_system(mocker, current_date, system_start, system_end, status):
    # cannot mock the datetime.date.today directly as it's written in C
    # https://docs.python.org/3/library/unittest.mock-examples.html#partial-mocking
    mock_date = mocker.patch("roadmap.models.date", wraps=date)
    mock_date.today.return_value = current_date

    app_stream = System(
        name="system-name",
        major=9,
        minor=6,
        lifecycle_type=LifecycleType.mainline,
        count=4,
        start_date=system_start,
        end_date=system_end,
    )

    assert app_stream.support_status == status


@pytest.mark.parametrize(
    ("name", "major", "minor", "expected"),
    (
        ("RHEL", 8, None, "RHEL 8"),
        ("RHEL", 9, 0, "RHEL 9.0"),
    ),
)
def test_get_rhel_display_name(name, major, minor, expected):
    assert _get_rhel_display_name(name, major, minor) == expected
