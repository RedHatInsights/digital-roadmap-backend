"""Security response headers are present on every response."""

import pytest

from fastapi.testclient import TestClient

from roadmap.security_headers import API_CONTENT_SECURITY_POLICY
from roadmap.security_headers import DOCS_PATHS
from roadmap.security_headers import SECURITY_HEADERS


PING = "/api/roadmap/v1/ping"


class TestAlwaysApplied:
    @pytest.mark.parametrize(("header", "value"), sorted(SECURITY_HEADERS.items()))
    def test_header_is_set(self, client, header, value):
        response = client.get(PING)

        assert response.headers[header] == value

    def test_api_responses_deny_everything(self, client):
        response = client.get(PING)

        assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY

    def test_hsts_is_left_to_the_edge(self, client):
        """TLS terminates at the edge; the application must not assert HSTS."""
        response = client.get(PING)

        assert "strict-transport-security" not in response.headers


class TestErrorResponses:
    """The headers middleware is outermost, so error responses carry them too."""

    def test_not_found(self, client):
        response = client.get("/api/roadmap/v1/no-such-route")

        assert response.status_code == 404
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY

    def test_method_not_allowed(self, client):
        response = client.post(PING)

        assert response.status_code == 405
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY

    def test_unhandled_exception(self, client):
        """A 500 is the case the middleware ordering exists for.

        logging_middleware re-raises after logging and returns its response
        from a finally block. The headers middleware has to sit outside that
        for the generated 500 to carry them.
        """
        route = "/_test_boom"
        app = client.app

        @app.get(route, include_in_schema=False)
        async def boom():
            raise RuntimeError("raised intentionally")

        # The exception has to become a response rather than propagate into
        # the test, which is what this client does differently.
        try:
            with TestClient(app, raise_server_exceptions=False) as tolerant_client:
                response = tolerant_client.get(route)

            assert response.status_code == 500
            for header, value in SECURITY_HEADERS.items():
                assert response.headers[header] == value
            assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY
        finally:
            app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != route]


class TestDocs:
    """Swagger UI and ReDoc load their assets from a CDN, so the deny-all
    policy is not applied to them. The other headers still are."""

    @pytest.mark.parametrize("path", sorted(DOCS_PATHS))
    def test_no_content_security_policy(self, client, path):
        response = client.get(path)

        assert response.status_code == 200
        assert "content-security-policy" not in response.headers

    @pytest.mark.parametrize("path", sorted(DOCS_PATHS))
    def test_other_headers_still_apply(self, client, path):
        response = client.get(path)

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_the_schema_itself_is_an_api_response(self, client):
        """openapi.json is JSON, not a docs page, so it gets the strict policy."""
        response = client.get("/openapi.json")

        assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY
