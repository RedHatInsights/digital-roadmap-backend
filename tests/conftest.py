import pytest
from fastapi.testclient import TestClient

from roadmap.main import app


@pytest.fixture
def client():
    return TestClient(app)
