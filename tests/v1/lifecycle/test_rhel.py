import pytest

from roadmap.models import System


def test_rhel_lifecycle(client, api_prefix):
    response = client.get(f"{api_prefix}/lifecycle/rhel")
    data = response.json()["data"]
    names = {item.get("name") for item in data}

    assert len(data) > 0
    assert names == {"RHEL"}
    assert response.status_code == 200


def test_rhel_lifecycle_major_version(client, api_prefix):
    response = client.get(f"{api_prefix}/lifecycle/rhel/9")
    data = response.json()["data"]
    names = {item.get("name") for item in data}
    versions = {item.get("major") for item in data}

    assert len(data) > 0
    assert names == {"RHEL"}
    assert versions == {9}
    assert response.status_code == 200


@pytest.mark.parametrize("params", ("9/0", "9/1", "8/2", "8/0"))
def test_rhel_lifecycle_major_minor_version(client, api_prefix, params):
    response = client.get(f"{api_prefix}/lifecycle/rhel/{params}")
    data = response.json()["data"]
    names = {item.get("name") for item in data}
    major = data[0]["major"]
    minor = data[0]["minor"]

    assert response.status_code == 200
    assert len(data) == 1
    assert names == {"RHEL"}
    assert (major, minor) == tuple(int(v) for v in params.split("/"))


def test_rhel_relevant(client, api_prefix, mocker, yield_json_fixture):
    mock_inventory_response = yield_json_fixture("inventory_db_response.json.gz")
    mock_rbac_response = [
        {
            "permission": "inventory:*:*",
            "resourceDefinitions": [],
        }
    ]
    mocker.patch("roadmap.v1.lifecycle.rhel.query_rbac", return_value=mock_rbac_response)
    mocker.patch("roadmap.v1.lifecycle.rhel.query_host_inventory", return_value=mock_inventory_response)
    response = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    data = response.json()["data"]

    assert len(data) > 1
    assert data[0].keys() == System.model_fields.keys()


def test_get_relevant_rhel_no_rbac_access(api_prefix, client, mocker):
    mock_rbac_response = []
    mocker.patch("roadmap.v1.lifecycle.rhel.query_rbac", return_value=mock_rbac_response)
    mocker.patch("roadmap.v1.lifecycle.rhel.check_inventory_access", return_value=(False, []))

    result = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert result.status_code == 403
