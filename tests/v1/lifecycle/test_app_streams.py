import pytest


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


def test_get_relevant_app_stream(api_prefix, client):
    result = client.get(f"{api_prefix}/relevant/lifecycle/app-streams/")
    data = result.json().get("data", "")

    assert result.status_code == 200
    assert len(data) > 0
