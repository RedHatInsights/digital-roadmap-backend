from datetime import date

import pytest

from roadmap.data.app_streams import AppStreamPackage
from roadmap.models import LifecycleType
from roadmap.models import SupportStatus
from roadmap.v1.lifecycle.app_streams import AppStream
from roadmap.v1.lifecycle.app_streams import AppStreamImplementation


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
    names = set(item["module_name"] for item in data)

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
    module_names = set(module["module_name"] for module in data)

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
    mocker.patch("roadmap.v1.lifecycle.app_streams.AppStream", side_effect=ValueError("Raised intentionally"))

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams/")
    detail = result.json().get("detail", "")

    assert result.status_code == 400
    assert detail == "Raised intentionally"


def test_app_stream_missing_lifecycle_data():
    """Given a RHEL major version that there is not lifecycle data for,
    ensure the dates are set as expected.
    """
    app_stream = AppStream(
        name="something",
        stream="1",
        os_major=1,
        os_lifecycle=LifecycleType.mainline,
        support_status=SupportStatus.supported,
        count=4,
        impl=AppStreamImplementation.package,
        rolling=True,
    )

    assert app_stream.start_date == date(1111, 11, 11)


def test_app_stream_package_no_start_date():
    """If no start_date is supplied, ensure the correct start date is added
    based on the initial_product_version.
    """
    package = AppStreamPackage(
        name="aardvark-dns",
        application_stream_name="container-tools",
        end_date=date(1111, 11, 11),
        initial_product_version="9.2",
        stream="1.5.0",
        lifecycle=0,
        rolling=True,
    )

    assert package.start_date == date(2023, 5, 10)


def test_app_stream_package_missing_rhel_data():
    """If no start_date is supplied and there is no RHEL lifecycle data available
    ensure the date is set to 1111-11-11.
    """
    package = AppStreamPackage(
        name="aardvark-dns",
        application_stream_name="container-tools",
        end_date=date(1111, 11, 11),
        initial_product_version="5.0",
        stream="1.5.0",
        lifecycle=0,
        rolling=True,
    )

    assert package.start_date == date(1111, 11, 11)


def test_app_stream_package_single_digit():
    """If a single digit is given for initial_product_version,
    os_minor should be set to None.
    """
    package = AppStreamPackage(
        name="aardvark-dns",
        application_stream_name="container-tools",
        end_date=date(1111, 11, 11),
        initial_product_version="9",
        stream="1.5.0",
        lifecycle=0,
        rolling=True,
    )

    assert package.os_minor is None
