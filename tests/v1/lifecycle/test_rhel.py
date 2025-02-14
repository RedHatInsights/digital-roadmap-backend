from operator import itemgetter

import pytest

import roadmap


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
def test_system_specified(client, api_prefix, source_data, path, response, monkeypatch):
    monkeypatch.setattr(roadmap.v1.lifecycle.rhel, "OS_DATA_MOCKED", source_data)
    data = client.get(f"{api_prefix}/lifecycle/rhel{path}")
    assert data.json() == sorted(response, key=itemgetter("major", "minor"), reverse=True)
