from datetime import date

import pytest

from roadmap.models import _get_rhel_display_name
from roadmap.models import LifecycleType
from roadmap.models import System
from tests.utils import SUPPORT_STATUS_TEST_CASES


@pytest.mark.parametrize(("current_date", "system_start", "system_end", "expected_status"), SUPPORT_STATUS_TEST_CASES)
def test_calculate_support_status_system(mocker, current_date, system_start, system_end, expected_status):
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

    assert app_stream.support_status == expected_status


@pytest.mark.parametrize(
    ("name", "major", "minor", "expected"),
    (
        ("RHEL", 8, None, "RHEL 8"),
        ("RHEL", 9, 0, "RHEL 9.0"),
    ),
)
def test_get_rhel_display_name(name, major, minor, expected):
    assert _get_rhel_display_name(name, major, minor) == expected
