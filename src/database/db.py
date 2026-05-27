from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from src.database.config import settings

engine = create_async_engine(
    settings.db_url, pool_size=5, max_overflow=10, pool_timeout=30, echo=True
)

async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
async_session_maker_null_pool = async_sessionmaker(
    bind=engine, poolclass=NullPool, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass
