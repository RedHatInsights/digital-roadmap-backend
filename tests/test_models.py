from datetime import date

import pytest

from roadmap.models import _get_rhel_display_name
from roadmap.models import _get_system_uuids
from roadmap.models import LifecycleType
from roadmap.models import SupportStatus
from roadmap.models import System
from tests.utils import SUPPORT_STATUS_TEST_CASES


@pytest.mark.parametrize(
    ("current_date", "system_start", "system_end", "expected_status"),
    SUPPORT_STATUS_TEST_CASES
    + (
        # Support ends within 3 months (90 days)
        (
            date(2027, 6, 15),
            date(2020, 1, 1),
            date(2027, 9, 1),
            SupportStatus.near_retirement,
        ),
        # Support ends within 6 months (180 days)
        # The RHEL release should still be considered supported.
        (
            date(2027, 6, 15),
            date(2020, 1, 1),
            date(2027, 12, 1),
            SupportStatus.supported,
        ),
    ),
)
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
        systems_detail=set(),
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


@pytest.mark.parametrize("count", (0, 1, 2))
def test_system_populate_systems_from_systems_details(make_systems, count):
    system_ids, systems_detail = make_systems(count)

    system_lifecycle = System(
        name="RHEL",
        major=9,
        minor=1,
        lifecycle_type=LifecycleType.mainline,
        count=count,
        start_date=date(2022, 5, 17),
        end_date=date(2032, 5, 31),
        systems_detail=systems_detail,
    )

    assert system_lifecycle.systems == system_ids


def test_get_system_uuids_attribute_not_existing():
    """Test if nonexisting name for getting UUIDs from result in empty set."""

    data = {"value": "value"}

    assert _get_system_uuids(data) == set()
