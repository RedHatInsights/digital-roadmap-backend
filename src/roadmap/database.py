# database.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from roadmap.config import SETTINGS


engine = create_async_engine(str(SETTINGS.database_url), echo=True)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Dependency to provide the database session
async def get_db():
    async with async_session() as session:
        yield session
