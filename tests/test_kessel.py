import pytest

from fastapi import HTTPException

from roadmap import kessel


def test_subject_from_identity_user():
    identity = {"type": "User", "user": {"user_id": "abc-123"}}

    subject = kessel.subject_from_identity(identity, "redhat")

    assert subject.resource.resource_id == "redhat/abc-123"
    assert subject.resource.resource_type == "principal"


def test_subject_from_identity_service_account():
    identity = {"type": "ServiceAccount", "service_account": {"user_id": "svc-9"}}

    subject = kessel.subject_from_identity(identity, "redhat")

    assert subject.resource.resource_id == "redhat/svc-9"


@pytest.mark.parametrize(
    "identity",
    (
        {},
        {"type": "System"},
        {"type": "User"},
        {"type": "User", "user": {}},
        {"type": "ServiceAccount", "service_account": {"user_id": ""}},
    ),
)
def test_subject_from_identity_no_user_id(identity):
    with pytest.raises(HTTPException, match="Not authorized to access host inventory"):
        kessel.subject_from_identity(identity, "redhat")


def test_host_groups_for(mocker):
    responses = [
        mocker.Mock(object=mocker.Mock(resource_id="grp-1")),
        mocker.Mock(object=mocker.Mock(resource_id="grp-2")),
    ]
    list_workspaces = mocker.patch("roadmap.kessel.list_workspaces", return_value=responses)
    client = mocker.Mock()
    subject = mocker.Mock()

    result = kessel.host_groups_for(client, subject)

    assert result == ["grp-1", "grp-2"]
    list_workspaces.assert_called_once_with(client, subject, kessel.HOST_VIEW_RELATION)


def test_org_wide_workspace_ids_cached(mocker):
    from roadmap.config import Settings

    kessel.reset_caches()
    mocker.patch("roadmap.kessel._auth_for_rbac", return_value=None)
    root = mocker.patch("roadmap.kessel.fetch_root_workspace", return_value=mocker.Mock(id="root-ws"))
    default = mocker.patch("roadmap.kessel.fetch_default_workspace", return_value=mocker.Mock(id="default-ws"))
    settings = Settings(rbac_hostname="example.com")

    first = kessel.org_wide_workspace_ids(settings, "1234")
    second = kessel.org_wide_workspace_ids(settings, "1234")

    assert first == frozenset({"root-ws", "default-ws"})
    assert second == first
    # Second call is served from cache.
    root.assert_called_once()
    default.assert_called_once()

    kessel.reset_caches()
