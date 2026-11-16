import base64
import gzip
import json

from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import pytest

from faker import Faker
from fastapi.testclient import TestClient

from roadmap.config import Settings
from roadmap.main import app
from roadmap.models import SystemInfo


#: Fixture host data is loaded under this org.
TEST_ORG_ID = "1234"


def encode_identity(org_id: str = TEST_ORG_ID, **user) -> str:
    """Build an x-rh-identity header value the way 3scale would."""
    payload = {"identity": {"org_id": org_id, "type": "User", "user": user}}
    return base64.b64encode(json.dumps(payload).encode()).decode()


@pytest.fixture(scope="function")
def identity_headers():
    return {"x-rh-identity": encode_identity()}


@pytest.fixture(scope="function")
def client(identity_headers):
    """TestClient that carries an identity header, as 3scale injects in production.

    decode_header rejects a request with no usable org_id, so a client without
    this header exercises the authentication failure rather than whatever the
    test means to cover. Use ``anonymous_client`` to test that rejection.
    """
    c = TestClient(app)
    c.headers.update(identity_headers)
    return c


@pytest.fixture(scope="function")
def anonymous_client():
    """TestClient that sends no identity header."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Unset these environment variables during testing"""
    unset = (
        "ROADMAP_DEV",
        "ROADMAP_KAFKA_BOOTSTRAP_SERVERS",
        "ROADMAP_KAFKA_NOTIFICATIONS_TOPIC",
        "ROADMAP_SUBSCRIPTIONS_URL",
        "ROADMAP_TLS_CERT_PATH",
        "ROADMAP_TLS_KEY_PATH",
    )
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
        if system_profile := system.get("system_profile"):
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


@pytest.fixture
def make_systems():
    fake = Faker()

    def _make_systems(count=3):
        systems = {
            SystemInfo(id=uuid4(), display_name=f"System {n}", os_major=fake.random_int(min=8, max=10), os_minor=None)
            for n in range(count)
        }
        system_ids = {system.id for system in systems}

        return system_ids, systems

    return _make_systems
