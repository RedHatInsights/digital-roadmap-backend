import sys

import pytest

from sentry_sdk.utils import BadDsn

from roadmap import common
from roadmap.main import app
from roadmap.v2.openapi import annotate_v2_openapi


def test_ping(client):
    response = client.get("/api/roadmap/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "pong"}


def test_metrics(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"roadmap_http_request" in response.read()


def test_openapi_docs_root(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert data["paths"]
    # Root schema keeps absolute path keys (M3)
    assert any(path.startswith("/api/roadmap/") for path in data["paths"])


def test_openapi_docs_v1(client):
    response = client.get("/api/roadmap/v1/openapi.json")

    assert response.status_code == 200
    data = response.json()
    paths = data["paths"]

    assert "/lifecycle/app-streams" in paths
    assert "/relevant/lifecycle/app-streams" in paths
    assert "/api/roadmap/v1/lifecycle/app-streams" not in paths
    assert not any(path.startswith("/api/roadmap") for path in paths)
    # v2-only systems endpoints must not leak into v1
    assert "/relevant/lifecycle/app-streams/systems" not in paths
    assert data["components"]["securitySchemes"]["Authorization"]["type"] == "apiKey"
    assert data["security"] == [{"Authorization": []}]
    assert "[NOT RECOMMENDED]" not in response.text
    assert "**Notice:** This endpoint is still in early development" not in response.text


def test_openapi_docs_v2(client):
    response = client.get("/api/roadmap/v2/openapi.json")

    assert response.status_code == 200
    data = response.json()
    paths = data["paths"]

    assert "/lifecycle/app-streams" in paths
    assert "/relevant/lifecycle/app-streams/systems" in paths
    assert not any(path.startswith("/api/roadmap") for path in paths)
    assert data["components"]["securitySchemes"]["Authorization"]["type"] == "apiKey"
    assert data["security"] == [{"Authorization": []}]

    notice = (
        "**Notice:** This endpoint is still in early development and is not recommended for use. "
        "Prefer the corresponding v1 endpoint where available."
    )
    operations = [
        operation
        for path_item in paths.values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    ]
    assert operations
    assert all(operation["summary"].startswith("[NOT RECOMMENDED] ") for operation in operations)
    assert all(operation["description"].startswith(notice) for operation in operations)


def test_openapi_schema_is_built_once_per_prefix(client, monkeypatch):
    """Each schema is generated once and served from cache thereafter."""
    app.openapi_schema = None
    app.state.openapi_schema_by_prefix = {}

    calls = []
    real_get_openapi = common.get_openapi

    def counting_get_openapi(**kwargs):
        calls.append(kwargs)
        return real_get_openapi(**kwargs)

    monkeypatch.setattr(common, "get_openapi", counting_get_openapi)

    for url in (
        "/openapi.json",
        "/api/roadmap/v1/openapi.json",
        "/api/roadmap/v2/openapi.json",
    ):
        first = client.get(url)
        second = client.get(url)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()

    assert len(calls) == 3  # one build per schema, not six


def test_openapi_docs_root_does_not_contain_v2_notice(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "[NOT RECOMMENDED]" not in response.text
    assert "**Notice:** This endpoint is still in early development" not in response.text


def test_annotate_v2_openapi_handles_existing_and_empty_metadata():
    notice = (
        "**Notice:** This endpoint is still in early development and is not recommended for use. "
        "Prefer the corresponding v1 endpoint where available."
    )
    schema = {
        "paths": {
            "/empty": {
                "get": {},
                "parameters": {},
                "delete": [],
            },
            "/existing": {
                "post": {
                    "summary": "Existing summary",
                    "description": "Existing description",
                },
                "put": {
                    "summary": "[NOT RECOMMENDED] Existing summary",
                    "description": notice,
                },
            },
        }
    }

    result = annotate_v2_openapi(schema)

    assert result is schema
    assert schema["paths"]["/empty"]["get"] == {
        "summary": "[NOT RECOMMENDED]",
        "description": notice,
    }
    assert schema["paths"]["/existing"]["post"] == {
        "summary": "[NOT RECOMMENDED] Existing summary",
        "description": f"{notice}\n\nExisting description",
    }
    assert schema["paths"]["/existing"]["put"] == {
        "summary": "[NOT RECOMMENDED] Existing summary",
        "description": notice,
    }
    assert schema["paths"]["/empty"]["parameters"] == {}
    assert schema["paths"]["/empty"]["delete"] == []


def test_sentry_sdk_init(monkeypatch):
    try:
        sys.modules.pop("roadmap.main")
    except KeyError:
        pass

    monkeypatch.setenv("SENTRY_DSN", "foo")
    with pytest.raises(BadDsn):
        import roadmap.main  # noqa: F401
