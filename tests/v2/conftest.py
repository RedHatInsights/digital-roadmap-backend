import pytest


@pytest.fixture(scope="session")
def v2_prefix():
    return "/api/roadmap/v2"


@pytest.fixture(scope="session")
def v1_prefix():
    return "/api/roadmap/v1"
