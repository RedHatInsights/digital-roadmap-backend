from datetime import date
from uuid import uuid4

import pytest

from roadmap.models import _get_rhel_display_name
from roadmap.models import _get_system_uuids
from roadmap.models import LifecycleType
from roadmap.models import SupportStatus
from roadmap.models import System
from roadmap.models import SystemInfo
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
        system_names=[],
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


def test_get_system_uuids_with_multiple_systems():
    system1_id = uuid4()
    system2_id = uuid4()
    system3_id = uuid4()

    system_names = [
        SystemInfo(id=system1_id, display_name="System 1"),
        SystemInfo(id=system2_id, display_name="System 2"),
        SystemInfo(id=system3_id, display_name="System 3"),
    ]

    result = _get_system_uuids(system_names)

    assert result == [system1_id, system2_id, system3_id]
    assert len(result) == 3
    assert all(isinstance(uuid, type(system1_id)) for uuid in result)


def test_get_system_uuids_with_single_system():
    system_id = uuid4()
    system_names = [SystemInfo(id=system_id, display_name="System")]

    result = _get_system_uuids(system_names)

    assert result == [system_id]
    assert len(result) == 1


def test_get_system_uuids_with_empty_system_list():
    result = _get_system_uuids([])

    assert result == []
    assert len(result) == 0


def test_system_populate_systems_from_system_names():
    """Check if the systems are correcly set using validator."""
    system1_id = uuid4()
    system2_id = uuid4()
    system_names = [
        SystemInfo(id=system1_id, display_name="System 1"),
        SystemInfo(id=system2_id, display_name="System 2"),
    ]

    system = System(
        name="RHEL",
        major=9,
        minor=1,
        lifecycle_type=LifecycleType.mainline,
        count=2,
        start_date=date(2022, 5, 17),
        end_date=date(2032, 5, 31),
        system_names=system_names,
    )

    assert system.systems == [system1_id, system2_id]
    assert len(system.systems) == 2
