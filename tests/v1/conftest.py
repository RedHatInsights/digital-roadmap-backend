import pytest


@pytest.fixture(scope="session")
def api_prefix():
    return "/api/roadmap/v1"
