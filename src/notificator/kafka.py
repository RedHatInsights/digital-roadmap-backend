"""Kafka producer for sending notifications to the platform notification service.

This module provides a way to send notification payloads to a Kafka topic
(``platform.notifications.ingress``), which the platform notification service
consumes to deliver emails, webhooks, etc. to users.

Typical usage from the notificator entry point::

    async with kafka_producer() as producer:
        await producer.send_notification(payload)

The ``kafka_producer()`` context manager handles the full lifecycle:
connecting to Kafka (with retries), yielding a ready-to-use producer,
and cleanly disconnecting when done. If Kafka is not configured (e.g. in
local development without a broker), it yields a no-op producer that
silently skips sending.
"""

from __future__ import annotations

import asyncio
import json
import logging

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from notificator.notificator_config import MAX_RETRIES
from notificator.notificator_config import NotificatorSettings
from notificator.notificator_config import RETRY_INTERVAL


logger = logging.getLogger(__name__)


def _build_producer(settings: NotificatorSettings) -> AIOKafkaProducer:
    """Create an AIOKafkaProducer from the notificator settings."""
    return AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)


async def _start_producer(producer: AIOKafkaProducer) -> None:
    """Connect the producer to Kafka, retrying on failure.

    Kafka may not be immediately available when the notificator starts
    (e.g. during a rolling deployment). This function retries up to
    ``MAX_RETRIES`` times, waiting ``RETRY_INTERVAL`` seconds between
    attempts. If all attempts fail, the last ``KafkaError`` is re-raised.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Attempting to connect Kafka producer (attempt %d/%d).", attempt, MAX_RETRIES)
            await producer.start()
            logger.info("Kafka producer connected successfully.")
            return
        except KafkaError:
            logger.exception(
                "Failed to connect Kafka producer (attempt %d/%d), retrying in %d seconds.",
                attempt,
                MAX_RETRIES,
                RETRY_INTERVAL,
            )
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(RETRY_INTERVAL)


@asynccontextmanager
async def kafka_producer() -> AsyncIterator[KafkaProducer]:
    """Context manager that connects to Kafka and yields a ready-to-use producer.

    Use it with ``async with`` to ensure the connection is properly closed
    after sending messages::

        async with kafka_producer() as producer:
            await producer.send_notification({"org_id": "1234", ...})

    If no Kafka brokers are configured and dev mode is off (i.e. a production misconfiguration),
    a no-op producer is yielded instead — calls to send_notification will silently do nothing.
    """
    settings = NotificatorSettings.create()
    logger.info(
        "Kafka settings: dev=%s, bootstrap_servers=%s, topic=%s",
        settings.dev,
        settings.bootstrap_servers,
        settings.notifications_topic,
    )
    if settings.dev or settings.bootstrap_servers:
        producer = _build_producer(settings)
    else:
        logger.warning("No Kafka brokers configured, notifications will be skipped")
        yield KafkaProducer(producer=None, topic="")
        return

    await _start_producer(producer)
    try:
        yield KafkaProducer(producer=producer, topic=settings.notifications_topic)
    finally:
        await producer.stop()


class KafkaProducer:
    """Wrapper around AIOKafkaProducer for sending notification payloads.

    You don't create this directly — use the ``kafka_producer()`` context
    manager which handles connection setup and teardown.

    When Kafka is not available, the producer is created with
    ``producer=None`` and all ``send_notification`` calls are silently
    skipped (no-op mode).
    """

    def __init__(self, producer: AIOKafkaProducer | None, topic: str):
        self._producer = producer
        self._topic = topic

    async def send_notification(self, payload: dict) -> None:
        """Serialize ``payload`` as JSON and send it to the notifications Kafka topic.

        Does nothing if the producer is in no-op mode (Kafka not configured).
        """
        if self._producer is None:
            return
        msg = json.dumps(payload).encode("utf-8")
        await self._producer.send_and_wait(self._topic, msg)
        logger.info("Notification sent to topic %s", self._topic)
