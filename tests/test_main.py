import sys

import pytest

from sentry_sdk.utils import BadDsn


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
    assert "paths" in response.json()


def test_openapi_docs_v1(client):
    response = client.get("/api/roadmap/v1/openapi.json")

    assert response.status_code == 200
    assert "paths" in response.json()


def test_sentry_sdk_init(monkeypatch):
    try:
        sys.modules.pop("roadmap.main")
    except KeyError:
        pass

    monkeypatch.setenv("SENTRY_DSN", "foo")
    with pytest.raises(BadDsn):
        import roadmap.main  # noqa: F401
