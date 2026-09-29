import json
import pathlib

from unittest.mock import MagicMock

import pytest

from app_common_python import loadConfig

from roadmap.config import Settings


@pytest.fixture(autouse=True)
def unset_acg_config(monkeypatch):
    monkeypatch.delenv("ACG_CONFIG", raising=False)
    monkeypatch.delenv("ROADMAP_DB_NAME", raising=False)
    monkeypatch.delenv("ROADMAP_DB_USER", raising=False)
    monkeypatch.delenv("ROADMAP_DB_PASSWORD", raising=False)
    monkeypatch.delenv("ROADMAP_DB_HOST", raising=False)
    monkeypatch.delenv("ROADMAP_DB_PORT", raising=False)


def test_default_settings():
    assert Settings.create().db_user == "postgres"


def test_settings_db_user(monkeypatch):
    monkeypatch.setenv("ROADMAP_DB_USER", "test_db_user")

    assert Settings.create().db_user == "test_db_user"


def test_setting_from_clowder(monkeypatch, mocker):
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )

    settings = Settings.create()

    assert settings.db_user == "username"
    assert settings.rbac_url == "http://rbac-service.svc:8123"


def test_setting_from_clowder_no_rbac(monkeypatch, mocker, tmp_path, read_json_fixture):
    clowder_config = read_json_fixture("clowder_config.json")
    clowder_config.pop("endpoints")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(clowder_config))

    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch("roadmap.config.LoadedConfig", loadConfig(str(config)))

    settings = Settings.create()

    assert settings.db_user == "username"
    assert settings.rbac_url == ""


def test_rbac_config_defaults(monkeypatch):
    monkeypatch.delenv("ROADMAP_RBAC_HOSTNAME", raising=False)
    monkeypatch.delenv("ROADMAP_RBAC_PORT", raising=False)

    settings = Settings.create()

    assert settings.rbac_hostname == ""
    assert settings.rbac_port == 8000
    assert settings.rbac_url == ""


def test_rbac_config_env(monkeypatch):
    monkeypatch.setenv("ROADMAP_RBAC_HOSTNAME", "example.com")
    monkeypatch.setenv("ROADMAP_RBAC_PORT", "8080")
    settings = Settings.create()

    assert settings.rbac_hostname == "example.com"
    assert settings.rbac_port == 8080
    assert settings.rbac_url == "http://example.com:8080"


def test_rbac_config_env_override_clowder(monkeypatch):
    monkeypatch.setenv("ACG_CONFIG", "yes")
    monkeypatch.setenv("ROADMAP_DB_NAME", "roadtrip-db")
    monkeypatch.setenv("ROADMAP_DB_USER", "thelma")
    monkeypatch.setenv("ROADMAP_DB_PASSWORD", "FRS635")
    monkeypatch.setenv("ROADMAP_DB_HOST", "WOOF.com")
    monkeypatch.setenv("ROADMAP_DB_PORT", "6753")
    settings = Settings.create()

    assert settings.db_name == "roadtrip-db"
    assert settings.db_user == "thelma"
    assert settings.db_password.get_secret_value() == "FRS635"
    assert settings.db_host == "WOOF.com"
    assert settings.db_port == 6753
    assert (
        settings.database_url.encoded_string()
        == "postgresql+psycopg://thelma:FRS635@WOOF.com:6753/roadtrip-db"  # notsecret
    )


def test_rbac_config_env_partial_override_clowder(monkeypatch):
    monkeypatch.setenv("ACG_CONFIG", "yes")
    monkeypatch.setenv("ROADMAP_DB_NAME", "roadtrip-db")
    monkeypatch.setenv("ROADMAP_DB_USER", "thelma")
    settings = Settings.create()

    assert settings.db_name == "roadtrip-db"
    assert settings.db_user == "thelma"
    assert settings.db_password.get_secret_value() == "postgres"
    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert (
        settings.database_url.encoded_string()
        == "postgresql+psycopg://thelma:postgres@localhost:5432/roadtrip-db"  # notsecret
    )


# --- Clowder V2 dependency endpoint tests ---


def _mock_v2_endpoint(uri, ca_certificate=None, authenticated=True):
    """Create a mock V2 dependency endpoint object."""
    ep = MagicMock()
    ep.uri = uri
    ep.ca_certificate = ca_certificate
    ep.authenticated = authenticated
    return ep


def test_v2_rbac_endpoint_resolution(monkeypatch, mocker):
    """V2 endpoint available: rbac_url uses complete V2 URI."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch(
        "roadmap.config.get_v2_dependency_endpoint",
        return_value=_mock_v2_endpoint("https://rbac-service.svc:8443"),
    )

    settings = Settings.create()

    assert settings.rbac_url == "https://rbac-service.svc:8443"
    assert settings.rbac_url_v2 == "https://rbac-service.svc:8443"
    assert settings.rbac_v2_authenticated is True
    # V1 fields should not be populated when V2 resolves
    assert settings.rbac_hostname == ""
    assert settings.rbac_port == 8000


def test_v2_rbac_endpoint_with_ca_cert(monkeypatch, mocker):
    """V2 endpoint with CA certificate path stores it for TLS verification."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch(
        "roadmap.config.get_v2_dependency_endpoint",
        return_value=_mock_v2_endpoint(
            "https://rbac-service.svc:8443",
            ca_certificate="/cdapp/certs/rbac-ca.crt",
        ),
    )

    settings = Settings.create()

    assert settings.rbac_url == "https://rbac-service.svc:8443"
    assert settings.rbac_ca_cert == "/cdapp/certs/rbac-ca.crt"


def test_v2_rbac_endpoint_no_ca_cert(monkeypatch, mocker):
    """V2 endpoint without CA cert: rbac_ca_cert stays empty (system trust)."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch(
        "roadmap.config.get_v2_dependency_endpoint",
        return_value=_mock_v2_endpoint("https://rbac-service.svc:8443"),
    )

    settings = Settings.create()

    assert settings.rbac_url == "https://rbac-service.svc:8443"
    assert settings.rbac_ca_cert == ""


def test_v2_fallback_to_v1(monkeypatch, mocker):
    """V2 returns None: falls back to V1 flat endpoint list."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch("roadmap.config.get_v2_dependency_endpoint", return_value=None)

    settings = Settings.create()

    assert settings.rbac_url == "http://rbac-service.svc:8123"
    assert settings.rbac_hostname == "rbac-service.svc"
    assert settings.rbac_port == 8123
    assert settings.rbac_url_v2 == ""


def test_v2_empty_uri_fallback_to_v1(monkeypatch, mocker):
    """V2 returns endpoint with empty URI: falls back to V1."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch(
        "roadmap.config.get_v2_dependency_endpoint",
        return_value=_mock_v2_endpoint(""),
    )

    settings = Settings.create()

    assert settings.rbac_url == "http://rbac-service.svc:8123"
    assert settings.rbac_hostname == "rbac-service.svc"


def test_v2_no_clowder_defaults():
    """Without Clowder, V2 fields stay at defaults."""
    settings = Settings.create()

    assert settings.rbac_url_v2 == ""
    assert settings.rbac_ca_cert == ""
    assert settings.rbac_url == ""


def test_rbac_url_v2_property_precedence():
    """rbac_url property returns V2 URI when set, even if hostname is populated."""
    settings = Settings(
        rbac_hostname="old-host.svc",
        rbac_port=9999,
        rbac_url_v2="https://new-rbac.svc:8443",
    )

    assert settings.rbac_url == "https://new-rbac.svc:8443"


# --- V2 field validation tests ---


@pytest.mark.parametrize(
    "url",
    ("http://rbac.svc:8080", "https://rbac.svc:8443", ""),
)
def test_rbac_url_v2_valid(url):
    """Valid HTTP(S) URLs and empty string are accepted."""
    settings = Settings(rbac_url_v2=url)

    assert settings.rbac_url_v2 == url


def test_rbac_url_v2_invalid_scheme():
    """Non-HTTP(S) URLs are rejected by the validator."""
    with pytest.raises(ValueError, match="HTTP\\(S\\) URL"):
        Settings(rbac_url_v2="ftp://rbac.svc:21")


def test_rbac_ca_cert_empty_accepted():
    """Empty rbac_ca_cert is accepted (system trust)."""
    settings = Settings(rbac_ca_cert="")

    assert settings.rbac_ca_cert == ""


def test_rbac_ca_cert_valid_path(tmp_path):
    """Readable CA cert file path is accepted."""
    cert = tmp_path / "ca.crt"
    cert.write_text("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----\n")

    settings = Settings(rbac_ca_cert=str(cert))

    assert settings.rbac_ca_cert == str(cert)


def test_rbac_ca_cert_missing_path_warns(caplog):
    """Non-existent CA cert path logs a warning but does not reject."""
    with caplog.at_level("WARNING"):
        settings = Settings(rbac_ca_cert="/nonexistent/ca.crt")

    assert settings.rbac_ca_cert == "/nonexistent/ca.crt"
    assert "does not exist" in caplog.text


def test_v2_authenticated_preserved(monkeypatch, mocker):
    """V2 endpoint authenticated flag is stored in settings."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch(
        "roadmap.config.get_v2_dependency_endpoint",
        return_value=_mock_v2_endpoint("https://rbac.svc:8443", authenticated=True),
    )

    settings = Settings.create()

    assert settings.rbac_v2_authenticated is True


def test_v2_unauthenticated_preserved(monkeypatch, mocker):
    """V2 endpoint with authenticated=False stores False."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch(
        "roadmap.config.get_v2_dependency_endpoint",
        return_value=_mock_v2_endpoint("https://rbac.svc:8443", authenticated=False),
    )

    settings = Settings.create()

    assert settings.rbac_v2_authenticated is False


def test_v2_fallback_authenticated_defaults_false(monkeypatch, mocker):
    """When V2 returns None and V1 fallback is used, authenticated stays False."""
    monkeypatch.setenv("ACG_CONFIG", "yes")
    mocker.patch(
        "roadmap.config.LoadedConfig",
        loadConfig(pathlib.Path(__file__).parent / "fixtures" / "clowder_config.json"),
    )
    mocker.patch("roadmap.config.get_v2_dependency_endpoint", return_value=None)

    settings = Settings.create()

    assert settings.rbac_v2_authenticated is False
