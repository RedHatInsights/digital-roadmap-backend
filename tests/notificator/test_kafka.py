"""Tests for notificator.kafka — Kafka producer wrapper, retry logic, and context manager."""

# pyright: reportArgumentType=false

from __future__ import annotations

import json
import ssl

from types import SimpleNamespace

import pytest

from aiokafka.errors import KafkaError

from notificator.kafka import _build_producer
from notificator.kafka import _build_ssl_context
from notificator.kafka import _start_producer
from notificator.kafka import kafka_producer
from notificator.kafka import KafkaBrokersNotConfigured
from notificator.kafka import KafkaProducer

from .utils import FakeKafkaProducer


def _make_settings(
    *,
    dev=False,
    bootstrap_servers=None,
    kafka_ca_path=None,
    kafka_security_protocol="PLAINTEXT",
    kafka_sasl_mechanism=None,
    kafka_sasl_username=None,
    kafka_sasl_password=None,
    topic="test-topic",
):
    return SimpleNamespace(
        dev=dev,
        bootstrap_servers=["broker:9092"] if bootstrap_servers is None else bootstrap_servers,
        kafka_ca_path=kafka_ca_path,
        kafka_security_protocol=kafka_security_protocol,
        kafka_sasl_mechanism=kafka_sasl_mechanism,
        kafka_sasl_username=kafka_sasl_username,
        kafka_sasl_password=kafka_sasl_password,
        notifications_topic=topic,
    )


class TestBuildSSLContext:
    """_build_ssl_context: returns an SSLContext when security protocol requires SSL."""

    def test_returns_none_when_plaintext(self):
        """PLAINTEXT protocol (local dev) → no SSL context needed."""
        settings = _make_settings(kafka_ca_path=None, kafka_security_protocol="PLAINTEXT")
        assert _build_ssl_context(settings) is None

    def test_returns_ssl_context_with_ca_path(self, mocker):
        """SASL_SSL with CA path → delegates to aiokafka create_ssl_context with cafile."""
        mock_ctx = mocker.MagicMock(spec=ssl.SSLContext)
        mock_create = mocker.patch("notificator.kafka.create_ssl_context", return_value=mock_ctx)
        settings = _make_settings(
            kafka_ca_path="/tmp/kafka-ca.pem",
            kafka_security_protocol="SASL_SSL",
        )

        result = _build_ssl_context(settings)

        assert result is mock_ctx
        mock_create.assert_called_once_with(cafile="/tmp/kafka-ca.pem")

    def test_returns_ssl_context_with_system_cas_when_no_ca_path(self, mocker):
        """SASL_SSL without custom CA → uses system trust store (covers MSK certs)."""
        mock_ctx = mocker.MagicMock(spec=ssl.SSLContext)
        mock_create = mocker.patch("notificator.kafka.create_ssl_context", return_value=mock_ctx)
        settings = _make_settings(kafka_ca_path=None, kafka_security_protocol="SASL_SSL")

        result = _build_ssl_context(settings)

        assert result is mock_ctx
        mock_create.assert_called_once_with(cafile=None)


class TestBuildProducer:
    """_build_producer: wires full security config into the producer from settings."""

    def test_sasl_ssl_protocol_passes_all_security_params(self, mocker):
        """SASL_SSL path (MSK stage/prod): security_protocol, ssl_context, and SASL
        credentials must all be forwarded to AIOKafkaProducer."""
        mock_ctx = mocker.MagicMock(spec=ssl.SSLContext)
        mocker.patch("notificator.kafka._build_ssl_context", return_value=mock_ctx)
        mock_producer_cls = mocker.patch("notificator.kafka.AIOKafkaProducer")
        settings = _make_settings(
            bootstrap_servers=["broker:9096"],
            kafka_ca_path="/tmp/kafka-ca.pem",
            kafka_security_protocol="SASL_SSL",
            kafka_sasl_mechanism="SCRAM-SHA-512",
            kafka_sasl_username="user",
            kafka_sasl_password="secret",
        )

        _build_producer(settings)

        mock_producer_cls.assert_called_once_with(
            bootstrap_servers=["broker:9096"],
            security_protocol="SASL_SSL",
            ssl_context=mock_ctx,
            sasl_mechanism="SCRAM-SHA-512",
            sasl_plain_username="user",
            sasl_plain_password="secret",
        )

    def test_plaintext_protocol_no_ssl_no_sasl(self, mocker):
        """PLAINTEXT path (local dev): no SSL context, no SASL credentials."""
        mocker.patch("notificator.kafka._build_ssl_context", return_value=None)
        mock_producer_cls = mocker.patch("notificator.kafka.AIOKafkaProducer")
        settings = _make_settings(
            bootstrap_servers=["localhost:9092"],
            kafka_security_protocol="PLAINTEXT",
            kafka_sasl_mechanism=None,
            kafka_sasl_username=None,
            kafka_sasl_password=None,
        )

        _build_producer(settings)

        mock_producer_cls.assert_called_once_with(
            bootstrap_servers=["localhost:9092"],
            security_protocol="PLAINTEXT",
            ssl_context=None,
            sasl_mechanism=None,
            sasl_plain_username=None,
            sasl_plain_password=None,
        )


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

    async def test_kafka_producer_no_brokers_raises(self, mocker):
        """Without brokers (and dev=False), the context manager must raise
        KafkaBrokersNotConfigured — running without a broker is a fatal misconfiguration."""
        mocker.patch(
            "notificator.kafka.NotificatorSettings.create",
            return_value=_make_settings(dev=False, bootstrap_servers=[]),
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
            return_value=_make_settings(dev=True, bootstrap_servers=["broker:9092"], topic="my-topic"),
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
            return_value=_make_settings(dev=True, bootstrap_servers=["broker:9092"]),
        )
        mocker.patch("notificator.kafka._build_producer", return_value=fake)
        mocker.patch("notificator.kafka.KAFKA_RETRY_INTERVAL", 0)

        with pytest.raises(RuntimeError, match="boom"):
            async with kafka_producer():
                raise RuntimeError("boom")

        assert fake.stopped is True
