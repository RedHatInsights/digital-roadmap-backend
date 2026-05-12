"""Kafka producer for sending notifications to the platform notification service.

This module provides a way to send notification payloads to a Kafka topic
(``platform.notifications.ingress``), which the platform notification service
consumes to deliver emails, webhooks, etc. to users.

Typical usage from the notificator entry point::

    async with kafka_producer() as producer:
        await producer.send_notification(payload)

The ``kafka_producer()`` context manager handles the full lifecycle:
connecting to Kafka (with retries), yielding a ready-to-use producer,
and cleanly disconnecting when done. If Kafka is not configured,
``KafkaBrokersNotConfigured`` is raised.
"""

from __future__ import annotations

import asyncio
import json
import ssl

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from notificator.notificator_config import KAFKA_MAX_RETRIES
from notificator.notificator_config import KAFKA_RETRY_INTERVAL
from notificator.notificator_config import NotificatorSettings


logger = structlog.get_logger(__name__)


class KafkaBrokersNotConfigured(Exception):
    """Raised when kafka_producer() is called without any Kafka brokers configured."""


def _build_ssl_context(settings: NotificatorSettings) -> ssl.SSLContext | None:
    """Return an mTLS SSLContext if the TLS cert and key files are present, else None.

    In Clowder-managed environments (stage/prod) the cert and key are mounted
    at the paths from settings. In local dev the files are absent, so we skip
    SSL and fall back to a plain connection.
    """
    cert = Path(settings.tls_cert_path)
    key = Path(settings.tls_key_path)
    if not cert.exists() or not key.exists():
        return None
    ssl_context = ssl.create_default_context()
    ssl_context.load_cert_chain(certfile=str(cert), keyfile=str(key))
    logger.info("Kafka SSL context created")
    return ssl_context


def _build_producer(settings: NotificatorSettings) -> AIOKafkaProducer:
    """Create an AIOKafkaProducer from the notificator settings.

    Uses mTLS when TLS cert/key files are present (stage/prod Clowder mounts),
    otherwise connects without SSL (local dev).
    """
    ssl_context = _build_ssl_context(settings)
    if ssl_context:
        return AIOKafkaProducer(
            bootstrap_servers=settings.bootstrap_servers,  # pyright: ignore [reportArgumentType]
            security_protocol="SSL",
            ssl_context=ssl_context,
        )
    return AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)  # pyright: ignore [reportArgumentType]


async def _start_producer(producer: AIOKafkaProducer) -> None:
    """Connect the producer to Kafka, retrying on failure.

    Kafka may not be immediately available when the notificator starts
    (e.g. during a rolling deployment). This function retries up to
    ``KAFKA_MAX_RETRIES`` times, waiting ``KAFKA_RETRY_INTERVAL`` seconds between
    attempts. If all attempts fail, the last ``KafkaError`` is re-raised.
    """
    for attempt in range(1, KAFKA_MAX_RETRIES + 1):
        try:
            logger.info("Attempting to connect Kafka producer", attempt=attempt, max_retries=KAFKA_MAX_RETRIES)
            await producer.start()
            logger.info("Kafka producer connected successfully")
            return
        except KafkaError:
            logger.exception(
                "Failed to connect Kafka producer",
                attempt=attempt,
                max_retries=KAFKA_MAX_RETRIES,
                retry_interval_seconds=KAFKA_RETRY_INTERVAL,
            )
            if attempt == KAFKA_MAX_RETRIES:
                raise
            await asyncio.sleep(KAFKA_RETRY_INTERVAL)


@asynccontextmanager
async def kafka_producer() -> AsyncIterator[KafkaProducer]:
    """Context manager that connects to Kafka and yields a ready-to-use producer.

    Use it with ``async with`` to ensure the connection is properly closed
    after sending messages::

        async with kafka_producer() as producer:
            await producer.send_notification({"org_id": "1234", ...})

    Raises ``KafkaBrokersNotConfigured`` if no Kafka brokers are configured
    and dev mode is off — running without a broker is a fatal misconfiguration.
    """
    settings = NotificatorSettings.create()
    logger.info(
        "Kafka settings loaded",
        dev=settings.dev,
        bootstrap_servers=settings.bootstrap_servers,
        topic=settings.notifications_topic,
    )
    if settings.dev or settings.bootstrap_servers:
        producer = _build_producer(settings)
    else:
        raise KafkaBrokersNotConfigured("No Kafka brokers configured and dev mode is off")

    await _start_producer(producer)
    try:
        yield KafkaProducer(producer=producer, topic=settings.notifications_topic)
    finally:
        await producer.stop()


class KafkaProducer:
    """Wrapper around AIOKafkaProducer for sending notification payloads.

    You don't create this directly — use the ``kafka_producer()`` context
    manager which handles connection setup and teardown.
    """

    def __init__(self, producer: AIOKafkaProducer, topic: str):
        self._producer = producer
        self._topic = topic

    async def send_notification(self, payload: dict) -> None:
        """Serialize ``payload`` as JSON and send it to the notifications Kafka topic."""
        msg = json.dumps(payload).encode("utf-8")
        await self._producer.send_and_wait(self._topic, msg)
        logger.info("Notification sent to Kafka", topic=self._topic, org_id=payload.get("org_id"))
