"""Tests for notificator.kafka — Kafka producer wrapper, retry logic, and context manager."""

# pyright: reportArgumentType=false

from __future__ import annotations

import json

from types import SimpleNamespace

import pytest

from aiokafka.errors import KafkaError

from notificator.kafka import _start_producer
from notificator.kafka import kafka_producer
from notificator.kafka import KafkaBrokersNotConfigured
from notificator.kafka import KafkaProducer

from .utils import FakeKafkaProducer


class TestKafkaProducer:
    """KafkaProducer wrapper: real serialization, fake network layer."""

    async def test_send_notification_serializes_payload_as_json(self):
        """The real json.dumps + encode path runs; we verify the bytes
        round-trip back to the original dict to catch encoding bugs."""
        fake = FakeKafkaProducer()
        kp = KafkaProducer(producer=fake, topic="notifications")

        payload = {"org_id": "42", "data": [1, 2, 3], "nested": {"key": "value"}}
        await kp.send_notification(payload)

        assert len(fake.sent) == 1
        _, msg_bytes = fake.sent[0]
        assert json.loads(msg_bytes) == payload

    async def test_send_notification_routes_to_configured_topic(self):
        """The topic passed at construction time must appear in every sent
        message, ensuring misconfigured topic names are caught early."""
        fake = FakeKafkaProducer()
        kp = KafkaProducer(producer=fake, topic="platform.notifications.ingress")

        await kp.send_notification({"org_id": "1"})

        topic, _ = fake.sent[0]
        assert topic == "platform.notifications.ingress"

    async def test_send_notification_accumulates_messages_in_order(self):
        """Multiple sends on the same producer must be recorded in FIFO order
        so consumers see messages in the sequence they were produced."""
        fake = FakeKafkaProducer()
        kp = KafkaProducer(producer=fake, topic="t")

        for i in range(3):
            await kp.send_notification({"seq": i})

        assert len(fake.sent) == 3
        for i, (_, msg_bytes) in enumerate(fake.sent):
            assert json.loads(msg_bytes)["seq"] == i


class TestStartProducer:
    """_start_producer retry logic: real loop, fake producer.start()."""

    @pytest.fixture(autouse=True)
    def _fast_retries(self, mocker):
        """Zero-out the sleep interval so the retry loop runs instantly."""
        mocker.patch("notificator.kafka.KAFKA_RETRY_INTERVAL", 0)

    async def test_start_producer_connects_on_first_attempt(self):
        """Happy path: broker is available immediately, no retries needed."""
        fake = FakeKafkaProducer()

        await _start_producer(fake)

        assert fake.started is True

    async def test_start_producer_retries_on_transient_failure(self, mocker):
        """Simulates a broker that is temporarily unreachable; the retry loop
        must recover once the broker comes back before max retries."""
        mocker.patch("notificator.kafka.KAFKA_MAX_RETRIES", 3)
        fake = FakeKafkaProducer(start_errors=[KafkaError(), KafkaError()])

        await _start_producer(fake)

        assert fake.started is True
        assert len(fake._start_errors) == 0

    async def test_start_producer_raises_after_max_retries(self, mocker):
        """When the broker never becomes available, the last KafkaError must
        propagate so the caller can handle the permanent failure."""
        mocker.patch("notificator.kafka.KAFKA_MAX_RETRIES", 2)
        fake = FakeKafkaProducer(start_errors=[KafkaError(), KafkaError()])

        with pytest.raises(KafkaError):
            await _start_producer(fake)

    async def test_start_producer_attempt_count_matches_max_retries(self, mocker):
        """Verify the loop runs exactly KAFKA_MAX_RETRIES times before giving
        up — not one fewer (premature) or one more (off-by-one)."""
        max_retries = 4
        mocker.patch("notificator.kafka.KAFKA_MAX_RETRIES", max_retries)
        fake = FakeKafkaProducer(start_errors=[KafkaError()] * max_retries)

        with pytest.raises(KafkaError):
            await _start_producer(fake)

        assert len(fake._start_errors) == 0


class TestKafkaProducerContextManager:
    """kafka_producer() context manager: real lifecycle, mocked settings + builder."""

    def _make_settings(self, *, dev=False, bootstrap_servers=None, topic="test-topic"):
        return SimpleNamespace(
            dev=dev,
            bootstrap_servers=bootstrap_servers or [],
            notifications_topic=topic,
        )

    async def test_kafka_producer_no_brokers_raises(self, mocker):
        """Without brokers (and dev=False), the context manager must raise
        KafkaBrokersNotConfigured — running without a broker is a fatal misconfiguration."""
        mocker.patch(
            "notificator.kafka.NotificatorSettings.create",
            return_value=self._make_settings(dev=False, bootstrap_servers=[]),
        )

        with pytest.raises(KafkaBrokersNotConfigured, match="No Kafka brokers configured"):
            async with kafka_producer():
                pass

    async def test_kafka_producer_start_yield_stop_lifecycle(self, mocker):
        """Verify the full happy-path lifecycle: start() before yield,
        correct topic on the wrapper, and stop() after the block exits."""
        fake = FakeKafkaProducer()
        mocker.patch(
            "notificator.kafka.NotificatorSettings.create",
            return_value=self._make_settings(dev=True, bootstrap_servers=["broker:9092"], topic="my-topic"),
        )
        mocker.patch("notificator.kafka._build_producer", return_value=fake)
        mocker.patch("notificator.kafka.KAFKA_RETRY_INTERVAL", 0)

        async with kafka_producer() as producer:
            assert producer._topic == "my-topic"
            assert fake.started is True

        assert fake.stopped is True

    async def test_kafka_producer_stop_on_exception(self, mocker):
        """The finally clause must call stop() even when the body raises,
        preventing leaked connections on unexpected errors."""
        fake = FakeKafkaProducer()
        mocker.patch(
            "notificator.kafka.NotificatorSettings.create",
            return_value=self._make_settings(dev=True, bootstrap_servers=["broker:9092"]),
        )
        mocker.patch("notificator.kafka._build_producer", return_value=fake)
        mocker.patch("notificator.kafka.KAFKA_RETRY_INTERVAL", 0)

        with pytest.raises(RuntimeError, match="boom"):
            async with kafka_producer():
                raise RuntimeError("boom")

        assert fake.stopped is True
