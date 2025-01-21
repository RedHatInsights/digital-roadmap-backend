import pytest
from fastapi.testclient import TestClient

import app
from app.main import app as application

client = TestClient(application)


@pytest.mark.parametrize(
    ("source_data", "path", "response"),
    (
        (
            [{"major": 8, "minor": 3, "data": "data"}, {"major": 8, "minor": 4, "data": "data"}],
            "/8/3",
            [{"major": 8, "minor": 3, "data": "data"}],
        ),
        (
            [{"major": 8, "minor": 3, "data": "data"}, {"major": 9, "minor": 0, "data": "data"}],
            "/9/0",
            [{"major": 9, "minor": 0, "data": "data"}],
        ),
        ([{"major": 8, "minor": 3, "data": "data"}, {"major": 9, "minor": 0, "data": "data"}], "/9/20", []),
        ([], "/9/20", []),
        (
            [
                {"major": 8, "minor": 3, "data": "data"},
                {"major": 9, "minor": 0, "data": "data"},
                {"major": 8, "minor": 7, "data": "data"},
                {"major": 9, "minor": 2, "data": "data"},
            ],
            "/9",
            [
                {"major": 9, "minor": 0, "data": "data"},
                {"major": 9, "minor": 2, "data": "data"},
            ],
        ),
        (
            [
                {"major": 8, "minor": 3, "data": "data"},
                {"major": 9, "minor": 0, "data": "data"},
                {"major": 8, "minor": 7, "data": "data"},
                {"major": 9, "minor": 2, "data": "data"},
            ],
            "",
            [
                {"major": 8, "minor": 3, "data": "data"},
                {"major": 8, "minor": 7, "data": "data"},
                {"major": 9, "minor": 0, "data": "data"},
                {"major": 9, "minor": 2, "data": "data"},
            ],
        ),
    ),
)
def test_system_specified(source_data, path, response, monkeypatch):
    monkeypatch.setattr(app.v1.lifecycle.systems, "OS_DATA_MOCKED", source_data)

    data = client.get(f"/api/digital-roadmap/v1/lifecycle/systems{path}")
    assert data.json() == response
