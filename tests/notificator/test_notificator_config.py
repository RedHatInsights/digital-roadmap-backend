from types import SimpleNamespace

from notificator.notificator_config import DEV_BOOTSTRAP_SERVERS
from notificator.notificator_config import NOTIFICATIONS_TOPIC_REQUESTED
from notificator.notificator_config import NotificatorSettings


def _patch_clowder_broker(mocker, *, cacert=None, authtype=None, sasl=None):
    """Patch isClowderEnabled and LoadedConfig to simulate a single Clowder broker.

    Returns ``(broker, mock_config)`` so callers can configure ``mock_config.kafka_ca``
    or inspect other attributes as needed.
    """
    broker = SimpleNamespace(cacert=cacert, authtype=authtype, sasl=sasl)
    mock_config = mocker.MagicMock()
    mock_config.kafka.brokers = [broker]
    mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=True)
    mocker.patch("notificator.notificator_config.LoadedConfig", mock_config)
    return broker, mock_config


def test_create_returns_notificator_settings():
    settings = NotificatorSettings.create()
    assert isinstance(settings, NotificatorSettings)


def test_bootstrap_servers_dev_mode(monkeypatch):
    monkeypatch.setenv("ROADMAP_DEV", "1")

    settings = NotificatorSettings.create()

    assert settings.bootstrap_servers == DEV_BOOTSTRAP_SERVERS


def test_bootstrap_servers_clowder(mocker):
    mocker.patch("notificator.notificator_config.KafkaServers", ["broker-host:27015"])

    settings = NotificatorSettings.create()

    assert settings.bootstrap_servers == ["broker-host:27015"]


def test_notifications_topic_found(mocker):
    topic = mocker.MagicMock()
    topic.name = "actual-topic-name"
    mocker.patch(
        "notificator.notificator_config.KafkaTopics",
        {NOTIFICATIONS_TOPIC_REQUESTED: topic},
    )

    settings = NotificatorSettings.create()

    assert settings.notifications_topic == "actual-topic-name"


def test_notifications_topic_not_found(mocker):
    mocker.patch("notificator.notificator_config.KafkaTopics", {})

    settings = NotificatorSettings.create()

    assert settings.notifications_topic == NOTIFICATIONS_TOPIC_REQUESTED


def test_bootstrap_servers_env_override(monkeypatch):
    monkeypatch.setenv("ROADMAP_KAFKA_BOOTSTRAP_SERVERS", "host1:9092,host2:9092")

    settings = NotificatorSettings.create()

    assert settings.bootstrap_servers == ["host1:9092", "host2:9092"]


def test_bootstrap_servers_env_override_takes_precedence_over_dev(monkeypatch):
    monkeypatch.setenv("ROADMAP_DEV", "1")
    monkeypatch.setenv("ROADMAP_KAFKA_BOOTSTRAP_SERVERS", "custom:9092")

    settings = NotificatorSettings.create()

    assert settings.bootstrap_servers == ["custom:9092"]


def test_notifications_topic_env_override(monkeypatch):
    monkeypatch.setenv("ROADMAP_KAFKA_NOTIFICATIONS_TOPIC", "my.custom.topic")

    settings = NotificatorSettings.create()

    assert settings.notifications_topic == "my.custom.topic"


def test_dev_mode_does_not_affect_topic_resolution(monkeypatch, mocker):
    monkeypatch.setenv("ROADMAP_DEV", "1")
    topic = mocker.MagicMock()
    topic.name = "mapped-topic"
    mocker.patch(
        "notificator.notificator_config.KafkaTopics",
        {NOTIFICATIONS_TOPIC_REQUESTED: topic},
    )

    settings = NotificatorSettings.create()

    assert settings.bootstrap_servers == DEV_BOOTSTRAP_SERVERS
    assert settings.notifications_topic == "mapped-topic"


def test_inherits_base_settings():
    settings = NotificatorSettings.create()

    assert settings.db_user == "postgres"
    assert settings.db_name == "digital_roadmap"
    assert (
        settings.database_url.encoded_string()
        == "postgresql+psycopg://postgres:postgres@localhost:5432/digital_roadmap"
    )


class TestKafkaBroker:
    """_kafka_broker: Clowder broker resolution edge-cases."""

    def test_returns_none_when_clowder_disabled(self, mocker):
        """No Clowder at all → _kafka_broker returns None."""
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=False)
        settings = NotificatorSettings.create()
        assert settings._kafka_broker() is None

    def test_returns_none_when_kafka_brokers_list_is_empty(self, mocker):
        """Clowder is active but the brokers list is empty → _kafka_broker returns None."""
        mock_config = mocker.MagicMock()
        mock_config.kafka.brokers = []
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=True)
        mocker.patch("notificator.notificator_config.LoadedConfig", mock_config)

        settings = NotificatorSettings.create()

        assert settings._kafka_broker() is None

    def test_returns_first_broker_when_clowder_configured(self, mocker):
        """Clowder provides brokers → first one is returned."""
        _, mock_config = _patch_clowder_broker(mocker, cacert=None)
        first_broker = mock_config.kafka.brokers[0]

        settings = NotificatorSettings.create()

        assert settings._kafka_broker() is first_broker


class TestKafkaCaPath:
    """kafka_ca_path: CA certificate path resolution."""

    def test_returns_none_when_no_broker(self, mocker):
        """No Clowder broker configured → no CA path."""
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=False)
        settings = NotificatorSettings.create()
        assert settings.kafka_ca_path is None

    def test_returns_none_when_broker_has_no_cacert(self, mocker):
        """Broker present but cacert is falsy → no CA path."""
        _patch_clowder_broker(mocker, cacert=None)
        settings = NotificatorSettings.create()
        assert settings.kafka_ca_path is None

    def test_returns_path_when_broker_has_cacert(self, mocker):
        """Broker with a CA cert → LoadedConfig.kafka_ca() result is returned."""
        _, mock_config = _patch_clowder_broker(mocker, cacert="-----BEGIN CERTIFICATE-----")
        mock_config.kafka_ca.return_value = "/tmp/kafka-ca.pem"

        settings = NotificatorSettings.create()

        assert settings.kafka_ca_path == "/tmp/kafka-ca.pem"
        mock_config.kafka_ca.assert_called_once()

    def test_returns_none_when_loaded_config_is_none_despite_broker_cacert(self, mocker):
        """Defensive branch: even if _kafka_broker() returns a broker with a cacert,
        a None LoadedConfig must not cause an AttributeError — returns None instead."""
        broker = SimpleNamespace(cacert="cert-content")
        mocker.patch.object(NotificatorSettings, "_kafka_broker", return_value=broker)
        mocker.patch("notificator.notificator_config.LoadedConfig", None)

        settings = NotificatorSettings.create()

        assert settings.kafka_ca_path is None


class TestKafkaSecurityProtocol:
    """kafka_security_protocol: PLAINTEXT vs SASL_SSL detection."""

    def test_returns_plaintext_when_no_broker(self, mocker):
        """No Clowder broker → fall back to PLAINTEXT (local dev)."""
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=False)
        settings = NotificatorSettings.create()
        assert settings.kafka_security_protocol == "PLAINTEXT"

    def test_returns_sasl_ssl_for_sasl_broker(self, mocker):
        """Broker with SASL authtype → SASL_SSL protocol."""
        sasl_enum = mocker.patch("notificator.notificator_config.BrokerConfigAuthtypeEnum")
        sasl_sentinel = object()
        sasl_enum.SASL = sasl_sentinel
        _patch_clowder_broker(mocker, authtype=sasl_sentinel)

        settings = NotificatorSettings.create()

        assert settings.kafka_security_protocol == "SASL_SSL"

    def test_returns_plaintext_for_non_sasl_broker(self, mocker):
        """Broker present but authtype is not SASL → still PLAINTEXT."""
        _patch_clowder_broker(mocker, authtype=None)
        settings = NotificatorSettings.create()
        assert settings.kafka_security_protocol == "PLAINTEXT"


class TestKafkaSaslProperties:
    """kafka_sasl_mechanism / username / password: SASL credential resolution."""

    def test_sasl_mechanism_returns_none_when_no_broker(self, mocker):
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=False)
        settings = NotificatorSettings.create()
        assert settings.kafka_sasl_mechanism is None

    def test_sasl_mechanism_returns_none_when_broker_has_no_sasl(self, mocker):
        _patch_clowder_broker(mocker, sasl=None)
        settings = NotificatorSettings.create()
        assert settings.kafka_sasl_mechanism is None

    def test_sasl_mechanism_returns_uppercased_value(self, mocker):
        """Mechanism from Clowder is uppercased to match the aiokafka expectation."""
        sasl = SimpleNamespace(saslMechanism="scram-sha-512", username="u", password="p")
        _patch_clowder_broker(mocker, sasl=sasl)

        settings = NotificatorSettings.create()

        assert settings.kafka_sasl_mechanism == "SCRAM-SHA-512"

    def test_sasl_mechanism_returns_none_when_sasl_mechanism_is_falsy(self, mocker):
        sasl = SimpleNamespace(saslMechanism=None, username="u", password="p")
        _patch_clowder_broker(mocker, sasl=sasl)

        settings = NotificatorSettings.create()

        assert settings.kafka_sasl_mechanism is None

    def test_sasl_username_returns_none_when_no_broker(self, mocker):
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=False)
        settings = NotificatorSettings.create()
        assert settings.kafka_sasl_username is None

    def test_sasl_username_returns_none_when_broker_has_no_sasl(self, mocker):
        _patch_clowder_broker(mocker, sasl=None)
        settings = NotificatorSettings.create()
        assert settings.kafka_sasl_username is None

    def test_sasl_username_returns_username_when_configured(self, mocker):
        sasl = SimpleNamespace(saslMechanism="SCRAM-SHA-512", username="kafka-user", password="x")
        _patch_clowder_broker(mocker, sasl=sasl)

        settings = NotificatorSettings.create()

        assert settings.kafka_sasl_username == "kafka-user"

    def test_sasl_password_returns_none_when_no_broker(self, mocker):
        mocker.patch("notificator.notificator_config.isClowderEnabled", return_value=False)
        settings = NotificatorSettings.create()
        assert settings.kafka_sasl_password is None

    def test_sasl_password_returns_none_when_broker_has_no_sasl(self, mocker):
        _patch_clowder_broker(mocker, sasl=None)
        settings = NotificatorSettings.create()
        assert settings.kafka_sasl_password is None

    def test_sasl_password_returns_password_when_configured(self, mocker):
        sasl = SimpleNamespace(saslMechanism="SCRAM-SHA-512", username="u", password="s3cr3t")
        _patch_clowder_broker(mocker, sasl=sasl)

        settings = NotificatorSettings.create()

        assert settings.kafka_sasl_password == "s3cr3t"
