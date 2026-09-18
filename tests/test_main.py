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


def test_logging_middleware_does_not_swallow_exceptions(client, caplog):
    """An endpoint error propagates out of the middleware instead of being logged away."""

    @client.app.get("/_test/boom", include_in_schema=False)
    async def boom():
        raise RuntimeError("Raised intentionally")

    try:
        with pytest.raises(RuntimeError, match="Raised intentionally"):
            client.get("/_test/boom")
    finally:
        client.app.router.routes = [r for r in client.app.router.routes if getattr(r, "path", None) != "/_test/boom"]

    assert "Uncaught exception" in caplog.text


def test_sentry_sdk_init(monkeypatch):
    try:
        sys.modules.pop("roadmap.main")
    except KeyError:
        pass

    monkeypatch.setenv("SENTRY_DSN", "foo")
    with pytest.raises(BadDsn):
        import roadmap.main  # noqa: F401
