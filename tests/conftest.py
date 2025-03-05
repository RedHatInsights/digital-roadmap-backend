import gzip
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

    def _read_json_file(file: str):
        if file.endswith(".gz"):
            with gzip.open(fixture_path.joinpath(file)) as gzfile:
                return json.load(gzfile)

        return json.loads(fixture_path.joinpath(file).read_text())

    return _read_json_file


@pytest.fixture
def read_fixture_file():
    fixture_path = Path(__file__).parent.joinpath("fixtures").resolve()

    def _read_file(file: Path, mode):
        with fixture_path.joinpath(file).open(mode) as f:
            data = f.read()

        return data

    return _read_file
