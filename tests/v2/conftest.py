import socket

import pytest


@pytest.fixture(scope="session")
def v2_prefix():
    return "/api/roadmap/v2"


@pytest.fixture(scope="session")
def v1_prefix():
    return "/api/roadmap/v1"


@pytest.fixture(scope="session")
def _db_available():
    """Probe the database once per session via a TCP connect. Returns True if reachable."""
    from roadmap.config import Settings

    settings = Settings.create()
    host = settings.database_url.hosts()[0]
    db_host = host.get("host", "localhost") or "localhost"
    db_port = host.get("port", 5432) or 5432

    try:
        sock = socket.create_connection((db_host, int(db_port)), timeout=2)
        sock.close()
        return True
    except OSError:
        return False


@pytest.fixture()
def requires_db(_db_available):
    """Skip the test if the database is not reachable."""
    if not _db_available:
        pytest.skip("PostgreSQL database not available — run `make start-db load-host-data`")
