from fastapi import APIRouter, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

import roadmap.v1

# Initialize FastAPI app
app = FastAPI()

# Add Prometheus metrics
instrumentor = Instrumentator()
instrumentor.instrument(app, metric_namespace="digital_roadmap")
instrumentor.expose(app)

# Create a main API router with the base prefix
api_router = APIRouter(prefix="/api/digital-roadmap", tags=["digital-roadmap"])

# Include individual service routers under the main API router
api_router.include_router(roadmap.v1.router)


@api_router.get("/v1/ping")
async def ping():
    return {"status": "pong"}


# Include the main API router in the FastAPI app
app.include_router(api_router)
