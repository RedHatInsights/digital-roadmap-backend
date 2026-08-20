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


def test_get_client_insecure(mocker):
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_url="localhost:9000", kessel_insecure=True)
    builder = mocker.Mock()
    stub = mocker.Mock()
    builder.build.return_value = (stub, mocker.Mock())
    client_builder = mocker.patch("roadmap.kessel.ClientBuilder", return_value=builder)

    result = kessel.get_client(settings)

    assert result is stub
    client_builder.assert_called_once_with("localhost:9000")
    builder.insecure.assert_called_once()
    builder.oauth2_client_authenticated.assert_not_called()
    builder.unauthenticated.assert_not_called()

    # Second call is served from the cached client.
    assert kessel.get_client(settings) is stub
    builder.build.assert_called_once()

    kessel.reset_caches()


def test_get_client_authenticated(mocker):
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_url="kessel:443", kessel_insecure=False, kessel_auth_enabled=True)
    builder = mocker.Mock()
    stub = mocker.Mock()
    builder.build.return_value = (stub, mocker.Mock())
    mocker.patch("roadmap.kessel.ClientBuilder", return_value=builder)
    creds = mocker.Mock()
    build_creds = mocker.patch("roadmap.kessel._build_credentials", return_value=creds)

    result = kessel.get_client(settings)

    assert result is stub
    build_creds.assert_called_once_with(settings)
    builder.oauth2_client_authenticated.assert_called_once_with(creds)
    builder.insecure.assert_not_called()

    kessel.reset_caches()


def test_get_client_unauthenticated(mocker):
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_url="kessel:443", kessel_insecure=False, kessel_auth_enabled=False)
    builder = mocker.Mock()
    stub = mocker.Mock()
    builder.build.return_value = (stub, mocker.Mock())
    mocker.patch("roadmap.kessel.ClientBuilder", return_value=builder)

    result = kessel.get_client(settings)

    assert result is stub
    builder.unauthenticated.assert_called_once()
    builder.insecure.assert_not_called()
    builder.oauth2_client_authenticated.assert_not_called()

    kessel.reset_caches()


def test_build_credentials(mocker):
    from roadmap.config import Settings

    settings = Settings(
        kessel_auth_oidc_issuer="https://sso.example.com/realms/redhat",
        kessel_auth_client_id="my-client",
        kessel_auth_client_secret="my-secret",
    )
    discovery = mocker.patch(
        "roadmap.kessel.fetch_oidc_discovery",
        return_value=mocker.Mock(token_endpoint="https://sso.example.com/token"),
    )
    oauth_creds = mocker.patch("roadmap.kessel.OAuth2ClientCredentials", return_value="creds")

    result = kessel._build_credentials(settings)

    assert result == "creds"
    discovery.assert_called_once_with("https://sso.example.com/realms/redhat")
    oauth_creds.assert_called_once_with(
        client_id="my-client",
        client_secret="my-secret",
        token_endpoint="https://sso.example.com/token",
    )
