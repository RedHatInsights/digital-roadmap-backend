import pytest


@pytest.fixture(scope="session")
def api_prefix():
    return "/api/digital-roadmap/v1"
