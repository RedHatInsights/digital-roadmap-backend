import logging
import os
import time

import sentry_sdk
import structlog

from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from uvicorn.protocols.utils import get_path_with_query_string

import roadmap.v1

from roadmap.config import Settings
from roadmap.common import extend_openapi
from roadmap.common import HealthCheckFilter
from roadmap.custom_logging import setup_logging


if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[
            FastApiIntegration(
                failed_request_status_codes={403, 404, *range(500, 599)},
                http_methods_to_capture=("GET",),
            ),
            StarletteIntegration(
                failed_request_status_codes={403, 404, *range(500, 599)},
                http_methods_to_capture=("GET",),
            ),
        ],
    )

# Setup logging
settings = Settings.create()
setup_logging(
    json_logs=settings.json_logging,
    log_level=settings.log_level.lower(),
)
access_logger = structlog.stdlib.get_logger("api.access")


# Initialize FastAPI app
app = FastAPI(
    title="Insights for RHEL Planning",
    summary="Major RHEL roadmap items as well as lifecycle data for RHEL and app streams.",
    redirect_slashes=False,
)
app.openapi = extend_openapi(app)


# Setup logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()
    # These context vars will be added to all log entries emitted during the request
    request_id = correlation_id.get()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.perf_counter_ns()
    # If the call_next raises an error, we still want to return our own 500 response,
    # so we can add headers to it (process time, request ID...)
    response = Response(status_code=500)
    try:
        response = await call_next(request)
    except Exception:
        # TODO: Validate that we don't swallow exceptions (unit test?)
        structlog.stdlib.get_logger("api.error").exception("Uncaught exception")
        raise
    finally:
        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code
        url = get_path_with_query_string(request.scope)
        client_host = request.client.host
        client_port = request.client.port
        http_method = request.method
        http_version = request.scope["http_version"]
        # Recreate the Uvicorn access log format, but add all parameters as structured information
        access_logger.info(
            f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            http={
                "url": str(request.url),
                "status_code": status_code,
                "method": http_method,
                "request_id": request_id,
                "version": http_version,
            },
            network={"client": {"ip": client_host, "port": client_port}},
            duration=process_time,
        )
        response.headers["X-Process-Time"] = str(process_time / 10**9)
        return response


# This middleware must be placed after the logging, to populate the context with the request ID,
# because middlewares are applied in the reverse order of when they are added.
app.add_middleware(CorrelationIdMiddleware)


# Add Prometheus metrics
instrumentor = Instrumentator()
instrumentor.instrument(app, metric_namespace="roadmap")
instrumentor.expose(app, include_in_schema=False)

# Create a main API router with the base prefix
api_router = APIRouter(prefix="/api/roadmap", tags=["Roadmap"])

# Additional route to the OpenAPI JSON under the versioned path
roadmap.v1.router.add_api_route("/openapi.json", app.openapi, include_in_schema=False)

# Include individual service routers under the main API router
api_router.include_router(roadmap.v1.router)


@api_router.get("/v1/ping", include_in_schema=False)
async def ping():
    return {"status": "pong"}


# Include the main API router in the FastAPI app
app.include_router(api_router)
