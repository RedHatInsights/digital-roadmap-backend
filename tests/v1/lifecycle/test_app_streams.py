from datetime import date
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from roadmap.common import decode_header
from roadmap.common import query_rbac
from roadmap.config import Settings
from roadmap.data.app_streams import AppStreamEntity
from roadmap.models import SupportStatus
from roadmap.v1.lifecycle.app_streams import AppStreamImplementation
from roadmap.v1.lifecycle.app_streams import NEVRA
from roadmap.v1.lifecycle.app_streams import RelevantAppStream
from tests.utils import SUPPORT_STATUS_TEST_CASES


def test_get_app_streams(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams")
    data = result.json().get("data", [])
    end_dates = {n["end_date"] for n in data}

    assert result.status_code == 200
    assert len(data) > 0
    assert "1111-11-11" not in end_dates


def test_get_app_streams_filter(api_prefix, client):
    result = client.get(
        f"{api_prefix}/lifecycle/app-streams", params={"kind": "package", "application_stream_name": "nginx"}
    )
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
    result = client.get(f"{api_prefix}/lifecycle/app-streams", params={"name": "nginx"})
    data = result.json().get("data", [])
    names = set(item["name"] for item in data)

    assert result.status_code == 200
    assert len(data) > 0
    assert names == {"nginx"}


@pytest.mark.parametrize("version", (8, 9))
def test_get_app_stream_package_names(api_prefix, client, version):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/{version}/packages")
    names = result.json().get("data", [])

    assert result.status_code == 200
    assert len(names) > 0


@pytest.mark.parametrize("version", (8, 9))
def test_get_app_stream_stream_names(api_prefix, client, version):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/{version}/streams")
    names = result.json().get("data", [])

    assert result.status_code == 200
    assert len(names) > 0


def test_get_app_stream_module_info(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/8", params={"name": "nginx"})
    data = result.json().get("data", "")
    module_names = set(module["name"] for module in data)

    assert result.status_code == 200
    assert len(data) > 0
    assert module_names == {"nginx"}


def test_get_app_stream_module_info_not_found(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/8", params={"name": "NOPE"})
    data = result.json().get("data", "")

    assert result.status_code == 200
    assert len(data) == 0


def test_get_relevant_app_stream(api_prefix, client):
    async def query_rbac_override():
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override
    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")
    data = result.json().get("data", "")

    assert result.status_code == 200
    assert len(data) > 0


def test_get_relevant_app_stream_error(api_prefix, client, mocker):
    def settings_override():
        return Settings(rbac_hostname="example.com")

    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        side_effect=HTTPError(url="url", code=400, hdrs=Message(), msg="Raised intentionally", fp=BytesIO()),
    )
    client.app.dependency_overrides = {}
    client.app.dependency_overrides[Settings.create] = settings_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")
    detail = result.json().get("detail", "")

    assert result.status_code == 400
    assert detail == "Raised intentionally"


def test_get_relevant_app_stream_error_building_response(api_prefix, client, mocker):
    async def query_rbac_override():
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override
    mocker.patch("roadmap.v1.lifecycle.app_streams.RelevantAppStream", side_effect=ValueError("Raised intentionally"))

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")
    detail = result.json().get("detail", "")

    assert result.status_code == 400
    assert detail == "Raised intentionally"


def test_get_relevant_app_stream_no_rbac_access(api_prefix, client):
    async def query_rbac_override():
        return [{}]

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")

    assert result.status_code == 403


def test_get_relevant_app_stream_resource_definitions(api_prefix, client):
    async def query_rbac_override():
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [
                    {
                        "attributeFilter": {
                            "key": "group.id",
                            "value": ["ebeaf62a-9713-4dad-8d63-32b51cadbda3"],
                            "operation": "in",
                        },
                    }
                ],
            }
        ]

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")
    assert result.status_code == 200


def test_get_relevant_app_stream_resource_definitions_with_group_restriction(api_prefix, client):
    """Testing a specific case that used to cause 501s"""

    # Note the restriction is on _groups_, not on _hosts_.
    async def query_rbac_override():
        return [
            {"permission": "inventory:hosts:read", "resourceDefinitions": []},
            {"permission": "inventory:groups:write", "resourceDefinitions": []},
            {"permission": "inventory:groups:read", "resourceDefinitions": []},
            {
                "permission": "inventory:groups:read",
                "resourceDefinitions": [
                    {
                        "attributeFilter": {
                            "key": "group.id",
                            "operation": "in",
                            "value": ["c22abc43-62f9-4a03-94e0-2a49d0e3c3d8"],
                        }
                    }
                ],
            },
        ]

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")

    assert result.status_code == 200


def test_get_relevant_app_stream_resource_definitions_with_ungrouped_permission(api_prefix, client):
    """
    Given a group with value None, which means "ungrouped", assert that only
    the host which belongs to the "ungrouped" group is returned.

    """

    async def query_rbac_override():
        return [
            {
                "permission": "inventory:hosts:read",
                "resourceDefinitions": [
                    {
                        "attributeFilter": {
                            "key": "group.id",
                            "operation": "in",
                            "value": [None],
                        }
                    }
                ],
            },
        ]

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override
    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams?related=true")
    data = result.json().get("data", "")
    assert result.status_code == 200
    assert len(data) == 1
    # In the test data there is an eligible system from another group (for
    # which the request does not have permission) that shows NGINX 1.14,
    # and another with NGINX 1.22.
    assert data[0]["display_name"] == "Node.js 18"


def test_get_relevant_app_stream_resource_definitions_with_ungrouped_and_grouped_permission(api_prefix, client):
    """Testing a case with group None, which means 'ungrouped', and another non-None group id"""

    async def query_rbac_override():
        return [
            {
                "permission": "inventory:hosts:read",
                "resourceDefinitions": [
                    {
                        "attributeFilter": {
                            "key": "group.id",
                            "operation": "in",
                            "value": [None, "aec18a86-3593-11f0-8426-5e43c8b8aa2f"],
                        }
                    }
                ],
            },
        ]

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override
    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams?related=true")
    data = result.json().get("data", "")
    # In the test data there is an eligible system from another group (for
    # which the request does not have permission) that shows NGINX 1.14.
    display_names = {d["display_name"] for d in data}
    assert {"Node.js 18", "NGINX 1.22"} == display_names
    assert result.status_code == 200


def test_get_revelent_app_stream_related(api_prefix, client, mocker):
    async def query_rbac_override():
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    async def decode_header_override():
        return "1234"

    # Set a specific date for today in order to test that app streams that are
    # already retired are not returned in the results.
    #
    # This test is specifically using the end_date of a FreeRADIUS 3.0
    # app stream that is 2029-05-31.
    #
    # The test data has a host with FreeRADIUS 2.8.
    mock_date = mocker.patch("roadmap.v1.lifecycle.app_streams.date", wraps=date)
    mock_date.today.return_value = date(2030, 6, 1)

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams", params={"related": True})
    data = result.json().get("data", "")
    related_count = sum(1 for item in data if item["related"])
    free_radius_streams = [n for n in data if "freeradius" in n["display_name"].casefold()]

    assert len(free_radius_streams) <= 2, "Got too many related app streams for FreeRADIUS"
    assert related_count, "No related items were returned"
    assert result.status_code == 200
    assert len(data) > 1


@pytest.mark.parametrize(
    "rbac",
    (
        [
            {
                "permission": "inventory:hosts:read",
                "resourceDefinitions": [
                    {
                        "attributeFilter": {
                            "key": "group.id",
                            "operation": "in",
                            "value": ["aec18a86-3593-11f0-8426-5e43c8b8aa2f", "397e1696-34f2-11f0-a718-5e43c8b8aa2f"],
                        }
                    }
                ],
            },
        ],
        [
            {
                "permission": "inventory:hosts:read",
                "resourceDefinitions": [
                    {
                        "attributeFilter": {
                            "key": "group.id",
                            "operation": "equal",
                            "value": "aec18a86-3593-11f0-8426-5e43c8b8aa2f",
                        }
                    }
                ],
            },
        ],
    ),
)
def test_get_revelent_app_stream_related_with_group_permissions(api_prefix, client, rbac):
    async def query_rbac_override():
        return rbac

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override
    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams?related=true")
    data = result.json().get("data", "")
    assert result.status_code == 200
    assert len(data) == 1
    # In the test data there is an eligible system from another group (for
    # which the request does not have permission) that shows NGINX 1.14,
    # and another with nodejs 18.
    assert data[0]["display_name"] == "NGINX 1.22"


def test_app_stream_missing_lifecycle_data():
    """Given a RHEL major version that there is no lifecycle data for,
    ensure the dates are set as expected.
    """
    app_stream = RelevantAppStream(
        name="something",
        display_name="Something 1",
        application_stream_name="App Stream Name",
        start_date=None,
        end_date=None,
        os_major=1,
        support_status=SupportStatus.supported,
        count=4,
        impl=AppStreamImplementation.package,
        rolling=True,
        systems=[],
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

    assert package.start_date is None


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
    (
        "current_date",
        "app_stream_start",
        "app_stream_end",
        "expected_status",
    ),
    SUPPORT_STATUS_TEST_CASES
    + (
        # Support ends within 3 months (90 days)
        #
        # Since a module is considered near retirement within six months, this
        # is also considered near retirement (3 < 6).
        (
            date(2027, 6, 15),
            date(2020, 1, 1),
            date(2027, 9, 1),
            SupportStatus.near_retirement,
        ),
        # Support ends within 6 months (180 days)
        (
            date(2027, 6, 15),
            date(2020, 1, 1),
            date(2027, 12, 1),
            SupportStatus.near_retirement,
        ),
    ),
)
def test_calculate_support_status_appstream(mocker, current_date, app_stream_start, app_stream_end, expected_status):
    # cannot mock the datetime.date.today directly as it's written in C
    # https://docs.python.org/3/library/unittest.mock-examples.html#partial-mocking
    mock_date = mocker.patch("roadmap.v1.lifecycle.app_streams.date", wraps=date)
    mock_date.today.return_value = current_date

    app_stream = RelevantAppStream(
        name="pkg-name",
        display_name="Pkg Name 1",
        application_stream_name="Pkg Name",
        os_major=1,
        os_minor=1,
        count=4,
        impl=AppStreamImplementation.package,
        rolling=False,
        start_date=app_stream_start,
        end_date=app_stream_end,
        systems=[],
    )

    assert app_stream.support_status == expected_status


@pytest.mark.parametrize(
    ("package", "expected"),
    (
        ("cairo-1.15.12-3.el8.x86_64", ("cairo", "0", "1", "15", "12", "3.el8", "x86_64")),
        ("rpm-build-libs-0:4.16.1.3-29.el9.x86_64", ("rpm-build-libs", "0", "4", "16", "1.3", "29.el9", "x86_64")),
        ("ansible-core-1:2.14.17-1.el9.x86_64", ("ansible-core", "1", "2", "14", "17", "1.el9", "x86_64")),
        ("NetworkManager-1:1.46.0-26.el9_4.x86_64", ("NetworkManager", "1", "1", "46", "0", "26.el9_4", "x86_64")),
        ("basesystem-0:11-13.el9.noarch", ("basesystem", "0", "11", "", "", "13.el9", "noarch")),
        (
            "abattis-cantarell-fonts-0:0.301-4.el9.noarch",
            ("abattis-cantarell-fonts", "0", "0", "301", "", "4.el9", "noarch"),
        ),
    ),
)
def test_from_string(package, expected):
    package = NEVRA.from_string(package)

    assert (
        package.name,
        package.epoch,
        package.major,
        package.minor,
        package.z,
        package.release,
        package.arch,
    ) == expected
