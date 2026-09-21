import os

from functools import lru_cache
from pathlib import Path

from app_common_python import isClowderEnabled
from app_common_python import LoadedConfig
from pydantic import FilePath
from pydantic import PostgresDsn
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


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

    # RBAC client timeouts. The 2000ms latency SLO is measured at the 3scale
    # gateway, so a slow RBAC call makes the entire request breach the SLO.
    # Fail fast instead of hanging 30s. Matches notifications-backend.
    rbac_timeout: float = 2.0
    rbac_connect_timeout: float = 1.0

    # Lifecycle endpoint response cache. These endpoints process the full org's
    # host inventory on every call, which takes ~1.5s for 15k hosts. Results
    # change slowly (only when hosts are added/removed or packages change via
    # the replication pipeline), so caching with a short TTL eliminates most
    # of the latency. Set ttl=0 to disable.
    #
    # maxsize bounds the number of cached responses, not their size. A response
    # holds a SystemInfo per host, measured at ~480 bytes each, so its cost
    # scales with the org: ~7 MiB for 15k hosts, ~23 MiB for 50k. Eight entries
    # is therefore a worst case of roughly 54 MiB (15k) to 187 MiB (50k) per
    # pod, against a 4 GiB request. Raise maxsize only with that in mind.
    lifecycle_cache_ttl: int = 60
    lifecycle_cache_maxsize: int = 8

    # Sentry samples every request by default, which adds span recording,
    # profile collection and network egress to each one. Sample a subset.
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

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

            # FIXME: Make RBAC setting in the environment override the clowder
            #        config file for consistency
            rbac = [endpoint for endpoint in endpoints if endpoint.app == "rbac"]
            rbac_kwargs = {}
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
