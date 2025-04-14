import os

from pathlib import Path

from roadmap.config import Settings


async def test_default_settings(monkeypatch):
    if os.environ.get("ACG_CONFIG") is not None:
        monkeypatch.delenv("ACG_CONFIG")
    if os.environ.get("ROADMAP_DB_USER") is not None:
        monkeypatch.delenv("ROADMAP_DB_USER")

    assert Settings.create().db_user == "postgres"

    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")
    assert Settings.create().db_user == "test_db_user"

    monkeypatch.setenv("ACG_CONFIG", os.path.join(os.getcwd(), "tests", "fixtures", "clowder_config.json"))
    assert Settings.create().db_user == "username"


async def test_environment_settings(monkeypatch):
    if os.environ.get("ACG_CONFIG") is not None:
        monkeypatch.delenv("ACG_CONFIG")
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")

    assert Settings.create().db_user == "test_db_user"


async def test_clowder_settings(monkeypatch):
    monkeypatch.setenv(
        "ACG_CONFIG", Path(__file__).parent.joinpath("fixtures").resolve().joinpath("clowder_config.json")
    )
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")

    assert Settings.create().db_user == "username"
