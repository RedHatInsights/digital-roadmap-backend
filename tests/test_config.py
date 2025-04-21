import os

from pathlib import Path

import pytest

from roadmap.config import Settings


@pytest.fixture(autouse=True)
def unset_acg_config(monkeypatch):
    monkeypatch.delenv("ACG_CONFIG", raising=False)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    Settings.create.cache_clear()


def test_default_settings(monkeypatch):
    monkeypatch.delenv("ROADMAP_DB_USER", raising=False)

    assert Settings.create().db_user == "postgres"


def test_settings_db_user(monkeypatch):
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")
    assert Settings.create().db_user == "test_db_user"


def test_setting_from_clowder(monkeypatch):
    monkeypatch.setenv("ACG_CONFIG", os.path.join(os.getcwd(), "tests", "fixtures", "clowder_config.json"))
    assert Settings.create().db_user == "username"


async def test_environment_settings(monkeypatch):
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")

    assert Settings.create().db_user == "test_db_user"


async def test_clowder_settings(monkeypatch):
    monkeypatch.setenv(
        "ACG_CONFIG", Path(__file__).parent.joinpath("fixtures").resolve().joinpath("clowder_config.json")
    )
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")

    settings = Settings.create()

    assert settings.db_user == "username"
    assert settings.rbac_url == "http://rbac-service.svc:8123"


def test_rbac_config_defaults(monkeypatch):
    monkeypatch.delenv("ROADMAP_RBAC_HOSTNAME", raising=False)
    monkeypatch.delenv("ROADMAP_RBAC_PORT", raising=False)

    settings = Settings.create()

    assert settings.rbac_hostname == ""
    assert settings.rbac_port == 8000
    assert settings.rbac_url == ""


def test_rbac_config_env(monkeypatch):
    monkeypatch.setenv("ROADMAP_RBAC_HOSTNAME", "example.com")
    monkeypatch.setenv("ROADMAP_RBAC_PORT", 8080)
    settings = Settings.create()

    assert settings.rbac_hostname == "example.com"
    assert settings.rbac_port == 8080
    assert settings.rbac_url == "http://example.com:8080"
