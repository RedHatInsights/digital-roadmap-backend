from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from roadmap.config import Settings


async def get_db(settings: Settings):
    engine = create_async_engine(str(settings.database_url), echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
