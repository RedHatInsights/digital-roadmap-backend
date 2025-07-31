import pytest


def test_get_app_streams(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams")
    data = result.json().get("data", [])
    end_dates = {n["end_date"] for n in data}

    assert result.status_code == 200
    assert len(data) > 0
    assert "1111-11-11" not in end_dates


@pytest.mark.parametrize(
    ("extra_params", "expected_count"),
    (
        ({"kind": "package"}, 1),
        ({"application_stream_type": "Application Stream"}, 9),
    ),
)
def test_get_app_streams_filter(api_prefix, client, extra_params, expected_count):
    params = {"application_stream_name": "nginx"} | extra_params
    result = client.get(f"{api_prefix}/lifecycle/app-streams", params=params)
    data = result.json().get("data", [])

    assert result.status_code == 200
    assert len(data) >= expected_count


@pytest.mark.parametrize("version", (8, 9, 10))
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
