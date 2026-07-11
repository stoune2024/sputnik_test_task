import os
from typing import Annotated, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


DB_URL = (
    f"postgresql+asyncpg://{os.environ.get('POSTGRES_USER')}:"
    f"{os.environ.get('POSTGRES_PASSWORD')}@{os.environ.get('POSTGRES_HOST')}:"
    f"{os.environ.get('PGPORT')}/{os.environ.get('POSTGRES_DB')}"
)
engine = create_async_engine(DB_URL)
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


SessionDep = Annotated[Any, Depends(get_session)]
