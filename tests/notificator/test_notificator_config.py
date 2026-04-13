from notificator.notificator_config import DEV_BOOTSTRAP_SERVERS
from notificator.notificator_config import NOTIFICATIONS_TOPIC_REQUESTED
from notificator.notificator_config import NotificatorSettings


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
