import typing as t

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from roadmap.config import Settings


async def get_db(settings: t.Annotated[Settings, Depends(Settings.create)]):
    engine = create_async_engine(str(settings.database_url), echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
