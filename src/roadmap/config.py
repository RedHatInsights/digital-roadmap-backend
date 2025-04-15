import os

from app_common_python import isClowderEnabled
from app_common_python import loadConfig
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
    def create(cls):
        """
        Create a settings object populated from presets, env and Clowder.

        Settings precedence:
        * Clowder's injected configuration json.
        * Environment variables with ROADMAP prefix. ex: ROADMAP_DB_NAME
        * Default values defined in the class attributes.

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
            rbac = [endpoint for endpoint in endpoints if endpoint.app == "rbac"]
            rbac_kwargs = {}
            if rbac:
                rbac = rbac.pop()
                rbac_kwargs = {
                    "rbac_hostname": rbac.hostname,
                    "rbac_port": rbac.port,
                }

            return cls(
                db_name=db.name,
                db_user=db.username,
                db_password=SecretStr(db.password),
                db_host=db.hostname,
                db_port=db.port,
                **rbac_kwargs,
            )

        return cls()


SETTINGS = Settings.create()
