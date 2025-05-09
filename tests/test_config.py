import json
import os

import pytest

from roadmap.config import Settings


@pytest.fixture(autouse=True)
def unset_acg_config(monkeypatch):
    monkeypatch.delenv("ACG_CONFIG", raising=False)


def test_default_settings(monkeypatch):
    monkeypatch.delenv("ROADMAP_DB_USER", raising=False)

    assert Settings.create().db_user == "postgres"


def test_settings_db_user(monkeypatch):
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")
    assert Settings.create().db_user == "test_db_user"


def test_setting_from_clowder(monkeypatch):
    monkeypatch.setenv("ACG_CONFIG", os.path.join(os.getcwd(), "tests", "fixtures", "clowder_config.json"))
    settings = Settings.create()
    assert settings.db_user == "username"
    assert settings.rbac_url == "http://rbac-service.svc:8123"


def test_setting_from_clowder_no_rbac(monkeypatch, tmp_path, read_json_fixture):
    clowder_config = read_json_fixture("clowder_config.json")
    clowder_config.pop("endpoints")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(clowder_config))
    monkeypatch.setenv("ACG_CONFIG", str(config))

    settings = Settings.create()

    assert settings.db_user == "username"
    assert settings.rbac_url == ""


def test_rbac_config_defaults(monkeypatch):
    monkeypatch.delenv("ROADMAP_RBAC_HOSTNAME", raising=False)
    monkeypatch.delenv("ROADMAP_RBAC_PORT", raising=False)

    settings = Settings.create()

    assert settings.rbac_hostname == ""
    assert settings.rbac_port == 8000
    assert settings.rbac_url == ""


def test_rbac_config_env(monkeypatch):
    monkeypatch.setenv("ROADMAP_RBAC_HOSTNAME", "example.com")
    monkeypatch.setenv("ROADMAP_RBAC_PORT", "8080")
    settings = Settings.create()

    assert settings.rbac_hostname == "example.com"
    assert settings.rbac_port == 8080
    assert settings.rbac_url == "http://example.com:8080"


def test_rbac_config_env_override_clowder(monkeypatch):
    monkeypatch.setenv("ACG_CONFIG", os.path.join(os.getcwd(), "tests", "fixtures", "clowder_config.json"))
    monkeypatch.setenv("ROADMAP_DB_NAME", "roadtrip-db")
    monkeypatch.setenv("ROADMAP_DB_USER", "thelma")
    monkeypatch.setenv("ROADMAP_DB_PASSWORD", "FRS635")
    monkeypatch.setenv("ROADMAP_DB_HOST", "WOOF.com")
    monkeypatch.setenv("ROADMAP_DB_PORT", "6753")
    settings = Settings.create()

    assert settings.db_name == "roadtrip-db"
    assert settings.db_user == "thelma"
    assert settings.db_password.get_secret_value() == "FRS635"
    assert settings.db_host == "WOOF.com"
    assert settings.db_port == 6753
    assert (
        settings.database_url.encoded_string()
        == "postgresql+psycopg://thelma:FRS635@WOOF.com:6753/roadtrip-db"  # notsecret
    )
