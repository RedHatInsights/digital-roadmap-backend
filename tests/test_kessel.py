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


@pytest.mark.asyncio
async def test_host_groups_for(mocker):
    responses = [
        mocker.Mock(object=mocker.Mock(resource_id="grp-1")),
        mocker.Mock(object=mocker.Mock(resource_id="grp-2")),
    ]

    async def _fake_list(*args, **kwargs):
        for r in responses:
            yield r

    mocker.patch("roadmap.kessel.list_workspaces_async", side_effect=_fake_list)
    client = mocker.Mock()
    subject = mocker.Mock()

    result = await kessel.host_groups_for(client, subject)

    assert result == ["grp-1", "grp-2"]


def test_get_client_insecure(mocker):
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_url="localhost:9000", kessel_insecure=True)
    builder = mocker.Mock()
    stub = mocker.Mock()
    builder.build_async.return_value = (stub, mocker.Mock())
    client_builder = mocker.patch("roadmap.kessel.ClientBuilder", return_value=builder)

    result = kessel.get_client(settings)

    assert result is stub
    client_builder.assert_called_once_with("localhost:9000")
    builder.insecure.assert_called_once()
    builder.oauth2_client_authenticated.assert_not_called()
    builder.unauthenticated.assert_not_called()

    # Second call is served from the cached client.
    assert kessel.get_client(settings) is stub
    builder.build_async.assert_called_once()

    kessel.reset_caches()


def test_get_client_authenticated(mocker):
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_url="kessel:443", kessel_insecure=False, kessel_auth_enabled=True)
    builder = mocker.Mock()
    stub = mocker.Mock()
    builder.build_async.return_value = (stub, mocker.Mock())
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
    builder.build_async.return_value = (stub, mocker.Mock())
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


# --- Service account token tests ---


def test_get_service_account_token_disabled():
    """kessel_auth_enabled=False → returns None immediately."""
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_auth_enabled=False)

    assert kessel.get_service_account_token(settings) is None
    kessel.reset_caches()


def test_get_service_account_token_no_creds():
    """No client_id/client_secret → returns None."""
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(kessel_auth_enabled=True, kessel_auth_client_id="", kessel_auth_client_secret="")

    assert kessel.get_service_account_token(settings) is None
    kessel.reset_caches()


def test_get_service_account_token_fetches_and_caches(mocker):
    """Valid credentials → fetches token from OIDC endpoint and caches it."""
    from roadmap.config import Settings
    from unittest.mock import MagicMock

    kessel.reset_caches()
    settings = Settings(
        kessel_auth_enabled=True,
        kessel_auth_client_id="my-client",
        kessel_auth_client_secret="my-secret",
        kessel_auth_oidc_issuer="https://sso.example.com/realms/redhat",
    )
    mocker.patch(
        "roadmap.kessel.fetch_oidc_discovery",
        return_value=mocker.Mock(token_endpoint="https://sso.example.com/token"),
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "tok-123", "expires_in": 300}
    mock_response.raise_for_status = MagicMock()
    mock_http_client = MagicMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
    mock_http_client.__exit__ = MagicMock(return_value=False)
    mocker.patch("roadmap.kessel.httpx.Client", return_value=mock_http_client)

    token = kessel.get_service_account_token(settings)

    assert token == "tok-123"
    mock_http_client.post.assert_called_once_with(
        "https://sso.example.com/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "my-client",
            "client_secret": "my-secret",
        },
    )

    # Second call uses cached token (no new HTTP call).
    token2 = kessel.get_service_account_token(settings)
    assert token2 == "tok-123"
    mock_http_client.post.assert_called_once()

    kessel.reset_caches()


def test_get_service_account_token_error_returns_none(mocker, caplog):
    """Token endpoint failure → returns None with warning."""
    from roadmap.config import Settings

    kessel.reset_caches()
    settings = Settings(
        kessel_auth_enabled=True,
        kessel_auth_client_id="my-client",
        kessel_auth_client_secret="my-secret",
        kessel_auth_oidc_issuer="https://sso.example.com/realms/redhat",
    )
    mocker.patch(
        "roadmap.kessel.fetch_oidc_discovery",
        side_effect=Exception("OIDC unreachable"),
    )

    with caplog.at_level("WARNING"):
        token = kessel.get_service_account_token(settings)

    assert token is None
    assert "Failed to fetch service account token" in caplog.text
    kessel.reset_caches()
