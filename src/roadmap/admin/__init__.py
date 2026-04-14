from fastapi import APIRouter
from fastapi import Depends

from . import notificator
from .auth import require_associate

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_associate)], include_in_schema=False)
router.include_router(notificator.router)
