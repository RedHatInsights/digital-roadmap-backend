from datetime import date

import pytest

from roadmap.data.app_streams import AppStreamEntity
from roadmap.models import LifecycleType
from roadmap.models import SupportStatus
from roadmap.v1.lifecycle.app_streams import AppStreamImplementation
from roadmap.v1.lifecycle.app_streams import RelevantAppStream


def test_get_app_streams(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams")
    data = result.json().get("data", [])

    assert result.status_code == 200
    assert len(data) > 0


@pytest.mark.parametrize("version", (8, 9))
def test_get_app_streams_by_version(api_prefix, client, version):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/{version}")
    data = result.json().get("data", [])

    assert result.status_code == 200
    assert len(data) > 0


def test_get_app_streams_by_name(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/", params={"name": "nginx"})
    data = result.json().get("data", [])
    names = set(item["name"] for item in data)

    assert result.status_code == 200
    assert len(data) > 0
    assert names == {"nginx"}


@pytest.mark.parametrize("version", (8, 9))
def test_get_app_stream_names(api_prefix, client, version):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/{version}/names")
    names = result.json().get("data", [])

    assert result.status_code == 200
    assert len(names) > 0


def test_get_app_stream_module_info(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/8/nginx")
    data = result.json().get("data", "")
    module_names = set(module["name"] for module in data)

    assert result.status_code == 200
    assert len(data) > 0
    assert module_names == {"nginx"}


def test_get_app_stream_module_info_not_found(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/8/NOPE")
    detail = result.json().get("detail", "")

    assert result.status_code == 404
    assert "no modules" in detail.lower()


def test_get_relevant_app_stream(api_prefix, client, mocker, read_json_fixture):
    mock_response = read_json_fixture("inventory_response_packages.json.gz")
    mocker.patch("roadmap.v1.lifecycle.app_streams.query_host_inventory", return_value=mock_response)

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams/")
    data = result.json().get("data", "")

    assert result.status_code == 200
    assert len(data) > 0


def test_get_relevant_app_stream_error(api_prefix, client, mocker, read_json_fixture):
    mock_response = read_json_fixture("inventory_response_packages.json.gz")
    mocker.patch("roadmap.v1.lifecycle.app_streams.query_host_inventory", return_value=mock_response)
    mocker.patch("roadmap.v1.lifecycle.app_streams.RelevantAppStream", side_effect=ValueError("Raised intentionally"))

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams/")
    detail = result.json().get("detail", "")

    assert result.status_code == 400
    assert detail == "Raised intentionally"


def test_app_stream_missing_lifecycle_data():
    """Given a RHEL major version that there is no lifecycle data for,
    ensure the dates are set as expected.
    """
    app_stream = RelevantAppStream(
        name="something",
        end_date=None,
        stream="1",
        os_major=1,
        os_lifecycle=LifecycleType.mainline,
        support_status=SupportStatus.supported,
        count=4,
        impl=AppStreamImplementation.package,
        rolling=True,
    )

    assert app_stream.start_date is None


def test_app_stream_package_no_start_date():
    """If no start_date is supplied, ensure the correct start date is added
    based on the initial_product_version.
    """
    package = AppStreamEntity(
        name="aardvark-dns",
        application_stream_name="container-tools",
        end_date=date(1111, 11, 11),
        initial_product_version="9.2",
        stream="1.5.0",
        lifecycle=0,
        rolling=True,
        impl=AppStreamImplementation.package,
    )

    assert package.start_date == date(2023, 5, 10)


def test_app_stream_package_missing_rhel_data():
    """If no start_date is supplied and there is no RHEL lifecycle data available
    ensure the date is set to 1111-11-11.
    """
    package = AppStreamEntity(
        name="aardvark-dns",
        application_stream_name="container-tools",
        end_date=date(1111, 11, 11),
        initial_product_version="5.0",
        stream="1.5.0",
        lifecycle=0,
        rolling=True,
        impl=AppStreamImplementation.package,
    )

    assert package.start_date == "Unknown"


def test_app_stream_package_single_digit():
    """If a single digit is given for initial_product_version,
    os_minor should be set to None.
    """
    package = AppStreamEntity(
        name="aardvark-dns",
        application_stream_name="container-tools",
        end_date=date(1111, 11, 11),
        initial_product_version="9",
        stream="1.5.0",
        lifecycle=0,
        rolling=True,
        impl=AppStreamImplementation.package,
    )

    assert package.os_minor is None


@pytest.mark.parametrize(
    ("current_date", "app_stream_start", "app_stream_end", "status"),
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
def test_calculate_support_status_appstream(mocker, current_date, app_stream_start, app_stream_end, status):
    # cannot mock the datetime.date.today directly as it's written in C
    # https://docs.python.org/3/library/unittest.mock-examples.html#partial-mocking
    mock_date = mocker.patch("roadmap.v1.lifecycle.app_streams.date", wraps=date)
    mock_date.today.return_value = current_date

    app_stream = RelevantAppStream(
        name="pkg-name",
        stream="1",
        os_major=1,
        os_minor=1,
        os_lifecycle=LifecycleType.mainline,
        count=4,
        impl=AppStreamImplementation.package,
        rolling=False,
        start_date=app_stream_start,
        end_date=app_stream_end,
    )

    assert app_stream.support_status == status
