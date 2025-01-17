from fastapi import APIRouter, FastAPI

from app.v1.lifecycle.router import v1_router as lifecycle_v1_router
from app.v1.released.endpoints import v1_router as released_v1_router
from app.v1.upcoming.endpoints import v1_router as upcoming_v1_router

# Initialize FastAPI app
app = FastAPI()

# Create a main API router with the /api prefix
api_router = APIRouter()

# Include individual service routers under the main API router
api_router.include_router(released_v1_router, prefix="/v1/release-notes", tags=["release-notes"])
api_router.include_router(upcoming_v1_router, prefix="/v1/upcoming-changes", tags=["upcoming-changes"])
api_router.include_router(lifecycle_v1_router, prefix="/v1/lifecycle")


@api_router.get("/v1/ping")
async def ping():
    return {"status": "pong"}


# Include the main API router in the FastAPI app with the prefix
app.include_router(api_router, prefix="/api/digital-roadmap", tags=["digital-roadmap"])
