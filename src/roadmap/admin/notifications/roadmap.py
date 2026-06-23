from notificator.notificator_config import ROADMAP_SUBSCRIPTION
from notificator.roadmap import roadmap_notification
from roadmap.admin.notifications import build_notification_router
from roadmap.admin.notifications import NotificationKind


kind = NotificationKind(label="roadmap", subscription=ROADMAP_SUBSCRIPTION, send=roadmap_notification)
router = build_notification_router(kind)
