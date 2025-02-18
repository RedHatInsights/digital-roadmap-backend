from pydantic import PostgresDsn
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ROADMAP_", env_ignore_empty=True)

    db_name: str = "digital_roadmap"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "localhost"
    db_port: int = 5432
    debug: bool = False
    dev: bool = False
    test: bool = False

    @property
    def database_url(self) -> PostgresDsn:
        return PostgresDsn(
            url=f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        )


SETTINGS = Settings()
