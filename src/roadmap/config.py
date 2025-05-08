import os

from functools import lru_cache
from pathlib import Path

from app_common_python import isClowderEnabled
from app_common_python import loadConfig
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
    debug: bool = False
    dev: bool = False
    host_inventory_url: str = "https://console.redhat.com"
    upcoming_json_path: FilePath = Path(__file__).parent.joinpath("data").joinpath("upcoming.json")
    test: bool = False
    rbac_hostname: str = ""
    rbac_port: int = 8000

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
        if isClowderEnabled():
            # ACG_CONFIG must refer to a json file.
            # Its contents populate LoadedConfig.

            # This is how Clowder docs tell you to do it:
            # db = LoadedConfig.database
            # However, that confounds our testing, so instead we do this:
            config = loadConfig(os.environ.get("ACG_CONFIG"))
            db = config.database
            endpoints = config.endpoints
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

            db_kwargs = {
                "db_name": db.name,
                "db_user": db.username,
                "db_password": SecretStr(db.password),
                "db_host": db.hostname,
                "db_port": db.port,
            }

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
                if os.getenv(v) is not None:
                    db_kwargs.pop(k)

            return cls(
                **db_kwargs,
                **rbac_kwargs,
            )

        return cls()
