import logging
import os

import sentry_sdk

from fastapi import APIRouter
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

import roadmap.v1

from roadmap.common import HealthCheckFilter


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

logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


# Initialize FastAPI app
app = FastAPI(redirect_slashes=False)

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
