import pytest


def test_get_app_streams(api_prefix, client):
    result = client.get(f"{api_prefix}/lifecycle/app-streams")

    assert result.status_code == 200
    assert len(result.json().get("data", [])) > 0


@pytest.mark.parametrize("version", (8, 9))
def test_get_app_stream_names(api_prefix, client, version):
    result = client.get(f"{api_prefix}/lifecycle/app-streams/{version}/names")

    assert result.status_code == 200
    assert len(result.json().get("names", [])) > 0
