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

    @property
    def database_url(self) -> PostgresDsn:
        return PostgresDsn(
            url=f"postgresql+psycopg://{self.db_user}:{self.db_password.get_secret_value()}@{self.db_host}:{self.db_port}/{self.db_name}"
        )

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
            db = loadConfig(os.environ.get("ACG_CONFIG")).database
            return cls(
                db_name=db.name,
                db_user=db.username,
                db_password=SecretStr(db.password),
                db_host=db.hostname,
                db_port=db.port,
            )

        return cls()


SETTINGS = Settings.create()
