import gzip
import json

from collections import defaultdict
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from roadmap.config import Settings
from roadmap.main import app


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Unset these environment variables during testing"""
    unset = ("ROADMAP_DEV",)
    for var in unset:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    Settings.create.cache_clear()


@pytest.fixture(scope="session")
def read_json_fixture():
    fixture_path = Path(__file__).parent.joinpath("fixtures").resolve()

    def _read_json_file(file: str):
        if file.endswith(".gz"):
            with gzip.open(fixture_path.joinpath(file)) as gzfile:
                return json.load(gzfile)

        return json.loads(fixture_path.joinpath(file).read_text())

    return _read_json_file


@pytest.fixture
def yield_json_fixture(read_json_fixture):
    async def _yield_fixture(file: str):
        for line in read_json_fixture(file):
            yield line

    return _yield_fixture


@pytest.fixture
def read_fixture_file():
    fixture_path = Path(__file__).parent.joinpath("fixtures").resolve()

    def _read_file(file: Path, mode):
        with fixture_path.joinpath(file).open(mode) as f:
            data = f.read()

        return data

    return _read_file


@pytest.fixture(scope="session")
def ids_by_os(read_json_fixture):
    data = read_json_fixture("inventory_db_response.json.gz")
    systems_by_version = defaultdict(set)
    for system in data:
        if system_profile := system.get("system_profile_facts"):
            key = system_profile.get("os_release")
            os = system_profile.get("operating_system")
            if os is not None:
                if not os.get("name"):
                    continue

                try:
                    key = f"{os['major']}.{os['minor']}"
                except KeyError:
                    pass

            systems_by_version[key].update([system["id"]])

    return systems_by_version
