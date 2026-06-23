from notificator.lifecycle import lifecycle_notification
from notificator.notificator_config import LIFECYCLE_SUBSCRIPTION

from roadmap.admin.notifications import NotificationKind
from roadmap.admin.notifications import build_notification_router

router = build_notification_router(
    NotificationKind(label="lifecycle", subscription=LIFECYCLE_SUBSCRIPTION, send=lifecycle_notification)
)
