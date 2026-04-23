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

from dataclasses import dataclass

from app_common_python import KafkaServers
from app_common_python import KafkaTopics

from roadmap.config import Settings


NOTIFICATIONS_TOPIC_REQUESTED = "platform.notifications.ingress"
DEV_BOOTSTRAP_SERVERS = ["localhost:9092"]
DEV_ORG_IDS = [1234]
KAFKA_RETRY_INTERVAL = 5
KAFKA_MAX_RETRIES = 5


@dataclass(frozen=True)
class SubscriptionType:
    """Identifies a Notifications Gateway subscription endpoint.

    *application* is the URL path segment appended to the base subscriptions URL
    (e.g. ``"life-cycle"`` or ``"roadmap"``).
    *event_type* is the ``eventTypeNames`` query-parameter value **and** the key
    used to look up org IDs in the JSON response.
    """

    application: str
    event_type: str


LIFECYCLE_SUBSCRIPTION = SubscriptionType("life-cycle", "retiring-lifecycle-monthly-report")
ROADMAP_SUBSCRIPTION = SubscriptionType("roadmap", "roadmap-monthly-report")

DEFAULT_TLS_CERT_PATH = "/tmp/tls/cert.pem"
DEFAULT_TLS_KEY_PATH = "/tmp/tls/key.pem"


class NotificatorSettings(Settings):
    """Extends Settings with Kafka-specific configuration for the notificator.

    All base settings (database, RBAC, etc.) are inherited from ``Settings``.
    The Kafka properties read from the Clowder config injected at deploy time,
    or use local defaults when ``ROADMAP_DEV=1``.
    """

    subscriptions_url: str | None = None
    tls_cert_path: str = DEFAULT_TLS_CERT_PATH
    tls_key_path: str = DEFAULT_TLS_KEY_PATH
    kafka_bootstrap_servers: str | None = None
    kafka_notifications_topic: str | None = None

    @classmethod
    def create(cls) -> NotificatorSettings:  # type: ignore[override]
        """Create a cached NotificatorSettings instance.

        Delegates to ``Settings.create()`` which handles Clowder and env var
        resolution. The parent's ``@lru_cache`` keys on ``cls``, so
        ``Settings.create()`` and ``NotificatorSettings.create()`` get
        separate cache entries automatically.
        """
        return super().create()  # type: ignore[return-value]

    @property
    def bootstrap_servers(self) -> list[str]:
        """Kafka broker addresses.

        Precedence: ``ROADMAP_KAFKA_BOOTSTRAP_SERVERS`` env var (comma-separated),
        then dev-mode localhost fallback, then Clowder-provided brokers.
        """
        if self.kafka_bootstrap_servers is not None:
            return [s.strip() for s in self.kafka_bootstrap_servers.split(",")]
        if self.dev:
            return DEV_BOOTSTRAP_SERVERS
        return KafkaServers

    @property
    def notifications_topic(self) -> str:
        """The Kafka topic name for the notification service.

        Precedence: ``ROADMAP_KAFKA_NOTIFICATIONS_TOPIC`` env var, then
        Clowder topic resolution, then the default requested topic name.
        """
        if self.kafka_notifications_topic is not None:
            return self.kafka_notifications_topic
        topic = KafkaTopics.get(NOTIFICATIONS_TOPIC_REQUESTED)
        if topic:
            return topic.name
        return NOTIFICATIONS_TOPIC_REQUESTED
