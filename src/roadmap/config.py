import logging
import os

from functools import lru_cache
from pathlib import Path

from app_common_python import get_v2_dependency_endpoint
from app_common_python import isClowderEnabled
from app_common_python import LoadedConfig
from pydantic import field_validator
from pydantic import FilePath
from pydantic import PostgresDsn
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


logger = logging.getLogger("uvicorn.error")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ROADMAP_", env_ignore_empty=True)

    db_name: str = "digital_roadmap"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")
    db_host: str = "localhost"
    db_port: int = 5432
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour (in seconds)
    debug: bool = False
    dev: bool = False
    host_inventory_url: str = "https://console.redhat.com"
    upcoming_json_path: FilePath = Path(__file__).parent.joinpath("data").joinpath("upcoming.json")
    test: bool = False
    rbac_hostname: str = ""
    rbac_port: int = 8000
    rbac_url_v2: str = ""  # Complete V2 URI (scheme://host:port), bypasses hostname+port
    rbac_ca_cert: str = ""  # V2 CA certificate filesystem path
    rbac_v2_authenticated: bool = False  # V2 endpoint requires workload authentication

    @field_validator("rbac_url_v2")
    @classmethod
    def _validate_rbac_url_v2(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("rbac_url_v2 must be an HTTP(S) URL")
        return v

    @field_validator("rbac_ca_cert")
    @classmethod
    def _validate_rbac_ca_cert(cls, v: str) -> str:
        if v:
            p = Path(v)
            if not p.is_file():
                logger.warning("rbac_ca_cert path does not exist or is not readable: %s", v)
            elif not os.access(v, os.R_OK):
                logger.warning("rbac_ca_cert path is not readable: %s", v)
        return v

    env_name: str = "stage"
    log_level: str = "info"
    json_logging: bool = False

    # Kessel / RBAC v2 authorization. When kessel_enabled is False (the default),
    # host authorization uses the legacy RBAC v1 /access/ path. When True, host
    # groups are determined via the Kessel gRPC Inventory API instead.
    kessel_enabled: bool = False
    kessel_url: str = ""
    kessel_insecure: bool = False
    kessel_auth_enabled: bool = True
    kessel_auth_client_id: str = ""
    kessel_auth_client_secret: SecretStr = SecretStr("")
    kessel_auth_oidc_issuer: str = ""
    kessel_principal_domain: str = "redhat"

    @property
    def database_url(self) -> PostgresDsn:
        return PostgresDsn(
            url=f"postgresql+psycopg://{self.db_user}:{self.db_password.get_secret_value()}@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def rbac_url(self) -> str:
        if self.rbac_url_v2:
            return self.rbac_url_v2

        if not self.rbac_hostname:
            return ""

        return f"http://{self.rbac_hostname}:{self.rbac_port}"

    @classmethod
    @lru_cache
    def create(cls) -> "Settings":
        """
        Create a settings object populated from presets, env and Clowder.

        Settings precedence:
        * Environment variables with ROADMAP prefix. ex: ROADMAP_DB_NAME
        * Clowder's injected configuration json.
        * Default values defined in the class attributes.

        The resason environment variables are preferred over the Clowder config file
        is because we want to use the database setting for the Host Inventory
        read replica as defined in the environment variables. We do not want
        to use the settings for the Roadmap database, which are inthe Clowder
        generated config.

        """
        # True if env var ACG_CONFIG is set.
        if isClowderEnabled() and LoadedConfig:
            db = LoadedConfig.database
            endpoints = LoadedConfig.endpoints

            # V2-first RBAC discovery: try the structured V2 dependency
            # endpoint, falling back to the legacy V1 flat endpoint list.
            rbac_kwargs = {}
            v2_ep = get_v2_dependency_endpoint("rbac", "service")
            if v2_ep is not None and v2_ep.uri:
                rbac_kwargs = {
                    "rbac_url_v2": v2_ep.uri,
                    "rbac_v2_authenticated": bool(getattr(v2_ep, "authenticated", False)),
                }
                if v2_ep.ca_certificate:
                    rbac_kwargs["rbac_ca_cert"] = v2_ep.ca_certificate
            else:
                # FIXME: Make RBAC setting in the environment override the
                #        clowder config file for consistency
                rbac = [endpoint for endpoint in endpoints if endpoint.app == "rbac"]
                if rbac:
                    rbac = rbac.pop()
                    rbac_kwargs = {
                        "rbac_hostname": rbac.hostname,
                        "rbac_port": rbac.port,
                    }

            db_kwargs = (
                {
                    "db_name": db.name,
                    "db_user": db.username,
                    "db_password": SecretStr(db.password),
                    "db_host": db.hostname,
                    "db_port": db.port,
                }
                if db
                else {}
            )

            env_check = {
                "db_name": "ROADMAP_DB_NAME",
                "db_user": "ROADMAP_DB_USER",
                "db_password": "ROADMAP_DB_PASSWORD",
                "db_host": "ROADMAP_DB_HOST",
                "db_port": "ROADMAP_DB_PORT",
            }
            # If the value is set as an env var, remove it from the kwargs so
            # that the default behavior of using the env var will take precedence.
            for k, v in env_check.items():
                if os.getenv(v) is not None and k in db_kwargs:
                    db_kwargs.pop(k)

            return cls(
                **db_kwargs,
                **rbac_kwargs,
            )

        return cls()
