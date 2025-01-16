import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def api_prefix():
    return "/api/digital-roadmap/v1"
