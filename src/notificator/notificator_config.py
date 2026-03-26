"""Configuration for the notificator, extending the base roadmap Settings with Kafka config.

In production, Kafka broker addresses and topic names are provided by the
Clowder platform via ``app_common_python``. In dev mode (``ROADMAP_DEV=1``),
the settings fall back to a plain local broker at ``localhost:9092``.

Usage::

    settings = NotificatorSettings.create()
    settings.bootstrap_servers      # Kafka broker addresses
    settings.notifications_topic    # resolved topic name
"""

from __future__ import annotations

from functools import lru_cache

from app_common_python import KafkaServers
from app_common_python import KafkaTopics

from roadmap.config import Settings


NOTIFICATIONS_TOPIC_REQUESTED = "platform.notifications.ingress"
DEV_BOOTSTRAP_SERVERS = "localhost:9092"
RETRY_INTERVAL = 5
MAX_RETRIES = 5


class NotificatorSettings(Settings):
    """Extends Settings with Kafka-specific configuration for the notificator.

    All base settings (database, RBAC, etc.) are inherited from ``Settings``.
    The Kafka properties read from the Clowder config injected at deploy time,
    or use local defaults when ``ROADMAP_DEV=1``.
    """

    @classmethod
    @lru_cache
    def create(cls) -> NotificatorSettings:  # type: ignore[override]
        """Create a cached NotificatorSettings instance.

        Delegates to ``Settings.create()`` which handles Clowder and env var
        resolution. The result is cached so repeated calls return the same instance.
        """
        return super().create()  # type: ignore[return-value]

    @property
    def bootstrap_servers(self) -> str | list[str]:
        """Kafka broker addresses. In dev mode, returns ``localhost:9092``."""
        if self.dev:
            return DEV_BOOTSTRAP_SERVERS
        return KafkaServers

    @property
    def notifications_topic(self) -> str:
        """The Kafka topic name for the notification service.

        Clowder may assign a different actual topic name than what we requested
        in ``deploy/config.yml``. This property resolves the requested name
        to the actual one via ``KafkaTopics``.
        """
        topic = KafkaTopics.get(NOTIFICATIONS_TOPIC_REQUESTED)
        if topic:
            return topic.name
        return NOTIFICATIONS_TOPIC_REQUESTED
