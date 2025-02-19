import json

from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from roadmap.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def read_json_fixture():
    fixture_path = Path(__file__).parent.joinpath("fixtures").resolve()

    def _read_json_file(file: Path):
        return json.loads(fixture_path.joinpath(file).read_text())

    return _read_json_file
