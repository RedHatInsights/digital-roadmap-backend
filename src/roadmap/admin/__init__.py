from fastapi import APIRouter

from . import notificator


router = APIRouter(prefix="/admin", tags=["Admin"], include_in_schema=False)
router.include_router(notificator.router)
