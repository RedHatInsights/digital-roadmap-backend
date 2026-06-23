from notificator.roadmap import roadmap_notification
from notificator.notificator_config import ROADMAP_SUBSCRIPTION

from roadmap.admin.notifications import NotificationKind
from roadmap.admin.notifications import build_notification_router

router = build_notification_router(
    NotificationKind(label="roadmap", subscription=ROADMAP_SUBSCRIPTION, send=roadmap_notification)
)
