import os

from roadmap.config import Settings

async def test_settings(monkeypatch):
    assert os.environ.get("ACG_CONFIG") is None
    assert os.environ.get("ROADMAP_DB_USER") is None
    
    from roadmap.config import SETTINGS
    assert SETTINGS.db_user == "postgres"

    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")
    assert Settings.create().db_user == "test_db_user"

    monkeypatch.setenv("ACG_CONFIG", 
                       os.path.join(os.getcwd(),
                                    'tests','fixtures','clowder_config.json'))
    assert Settings.create().db_user == "username"
