"""Security response headers.

The service answered with none of the usual hardening headers. The edge is the
right place for some of them and the wrong place for others, so this module is
deliberately narrow: it sets the headers whose correct value does not depend on
how the service is fronted, and leaves the rest to the edge.

Set here:

``X-Content-Type-Options: nosniff``
    Stops a browser from re-interpreting a JSON response as HTML or script.
    This endpoint returns attacker-influenced strings inside JSON (display
    names and package names come from customer inventory), so content sniffing
    is the realistic path from "data in a response" to "script in a page".

``X-Frame-Options: DENY``
    No part of this service is meant to be framed. Paired with the
    ``frame-ancestors`` directive below for browsers that prefer CSP.

``Referrer-Policy: no-referrer``
    Request URLs carry query parameters. Nothing downstream needs to know
    which page a request came from.

``Content-Security-Policy``
    A JSON API should load nothing at all, so the policy denies everything.
    See DOCS_PATHS for the exception.

Not set here:

``Strict-Transport-Security``
    TLS terminates at the edge; these pods speak plain HTTP. HSTS is sticky in
    the browser and a wrong ``max-age`` is difficult to undo, so emitting a
    second, possibly conflicting value from the application is worse than
    leaving the one authority that terminates TLS to set it. Confirm the edge
    does.
"""

from collections.abc import Awaitable
from collections.abc import Callable

from fastapi import Request
from fastapi import Response


#: Headers applied to every response.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

#: Policy for API responses. The service returns JSON and never needs to load
#: a script, a style, an image or a font, so the default is to allow nothing.
API_CONTENT_SECURITY_POLICY = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

#: Paths that serve the interactive API documentation. Swagger UI and ReDoc are
#: HTML pages that pull their script and stylesheet from a CDN, so the policy
#: above would leave them blank. They are excluded rather than given a
#: CDN-specific policy, which would break quietly whenever FastAPI changed the
#: CDN it points at. The other headers still apply to them.
#:
#: Worth noting separately: these pages, and the schema they render, are
#: reachable without authentication. Whether they should be served in
#: production at all is a question this module does not answer.
DOCS_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/redoc"})


def apply_security_headers(path: str, response: Response) -> None:
    """Add the security headers to ``response``, chosen by request path.

    Existing values are left alone, so a route that deliberately sets its own
    policy keeps it.
    """
    headers = dict(SECURITY_HEADERS)
    if path not in DOCS_PATHS:
        headers["Content-Security-Policy"] = API_CONTENT_SECURITY_POLICY

    for name, value in headers.items():
        response.headers.setdefault(name, value)


async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach the security headers on the way out.

    Registered last so it is the outermost middleware, which means error
    responses generated further in are covered too.
    """
    response = await call_next(request)
    apply_security_headers(request.url.path, response)
    return response
