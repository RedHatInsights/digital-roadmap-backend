from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from roadmap.config import Settings


SETTINGS = Settings.create()
ENGINE = create_async_engine(
    str(SETTINGS.database_url),
    echo=True,
    pool_size=SETTINGS.db_pool_size,
    max_overflow=SETTINGS.db_max_overflow,
)


async def get_db():
    # Docs for connections and transactions that explain pool_size and max_overflow
    #   https://docs.sqlalchemy.org/en/20/errors.html#error-3o7r

    async_session = async_sessionmaker(ENGINE, expire_on_commit=False)
    async with async_session() as session:
        yield session
