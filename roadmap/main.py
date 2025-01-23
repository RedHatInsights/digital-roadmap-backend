from fastapi import APIRouter, FastAPI

from roadmap.v1.lifecycle import v1_router as lifecycle_v1_router
from roadmap.v1.release_notes import v1_router as release_notes_v1_router
from roadmap.v1.upcoming import v1_router as upcoming_v1_router

# Initialize FastAPI app
app = FastAPI()

# Create a main API router with the /api prefix
api_router = APIRouter()

# Include individual service routers under the main API router
api_router.include_router(release_notes_v1_router, prefix="/v1/release-notes", tags=["release-notes"])
api_router.include_router(upcoming_v1_router, prefix="/v1/upcoming-changes", tags=["upcoming-changes"])
api_router.include_router(lifecycle_v1_router, prefix="/v1/lifecycle")


@api_router.get("/v1/ping")
async def ping():
    return {"status": "pong"}


# Include the main API router in the FastAPI app with the prefix
app.include_router(api_router, prefix="/api/digital-roadmap", tags=["digital-roadmap"])
