from notificator.lifecycle import lifecycle_notification
from notificator.notificator_config import LIFECYCLE_SUBSCRIPTION
from roadmap.admin.notifications import build_notification_router
from roadmap.admin.notifications import NotificationKind


kind = NotificationKind(label="lifecycle", subscription=LIFECYCLE_SUBSCRIPTION, send=lifecycle_notification)
router = build_notification_router(kind)
