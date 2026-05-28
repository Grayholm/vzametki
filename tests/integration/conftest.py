from httpx import ASGITransport, AsyncClient
import pytest

from src.notes.models import NotesModel # noqa: F401
from src.main import app  # noqa: F401

from src.database.db import Base, engine_null_pool


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Дропаем и создаём таблицы один раз за всю сессию."""
    async with engine_null_pool.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
async def ac():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac