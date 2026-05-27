import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.config import settings
from src.database.db import Base, engine, async_session_maker_null_pool
from src.notes.repository import NotesRepository
from src.notes.service import NotesService


@pytest.fixture(scope="session", autouse=True)
async def check_test_mode():
    assert settings.MODE == "test", f"MODE must be 'test', got '{settings.MODE}'"


@pytest.fixture(scope="session", autouse=True)
async def setup_database(check_test_mode):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def session():
    async with async_session_maker_null_pool() as session:
        yield session


@pytest.fixture
async def notes_repo(session: AsyncSession) -> NotesRepository:
    return NotesRepository(session)


@pytest.fixture
async def notes_service(
    session: AsyncSession, notes_repo: NotesRepository
) -> NotesService:
    return NotesService(session=session, repo=notes_repo)
