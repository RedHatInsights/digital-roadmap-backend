import pytest


def test_all_rhel(client, api_prefix):
    response = client.get(f"{api_prefix}/lifecycle/rhel")
    data = response.json()["data"]
    names = {item.get("name") for item in data}

    assert len(data) > 0
    assert names == {"RHEL"}
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (
            "/8/3",
            ("RHEL", 8, 3),
        ),
        (
            "/9/1",
            ("RHEL", 9, 1),
        ),
    ),
)
def test_rhel_major_minor(client, api_prefix, path, expected):
    response = client.get(f"{api_prefix}/lifecycle/rhel{path}")
    data = response.json()["data"][0]
    (name, major, minor) = data["name"], data["major"], data["minor"]

    assert response.status_code == 200
    assert (name, major, minor) == expected
