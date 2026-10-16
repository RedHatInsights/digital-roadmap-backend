import sys

import pytest

from sentry_sdk.utils import BadDsn

from roadmap import common
from roadmap.main import app


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


def test_sentry_sdk_init(monkeypatch):
    try:
        sys.modules.pop("roadmap.main")
    except KeyError:
        pass

    monkeypatch.setenv("SENTRY_DSN", "foo")
    with pytest.raises(BadDsn):
        import roadmap.main  # noqa: F401
