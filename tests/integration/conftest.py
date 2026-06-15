from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.core.service import NotesService
from src.infrastructure.db import Base, engine_null_pool, async_session_maker_null_pool
from src.core.models import NotesModel  # noqa: F401


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Дропаем и создаём таблицы один раз за всю сессию."""
    async with engine_null_pool.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(setup_database):
    async with async_session_maker_null_pool() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def ac(db_session):
    """HTTP-клиент к notes-service с замоканным DI."""

    async def _override_get_notes_service():
        return NotesService(session=db_session)

    from src.api.routers import get_notes_service
    app.dependency_overrides[get_notes_service] = _override_get_notes_service

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mocks():
    """Мокаем внешние сервисы — только БД реальная."""
    with (
        patch("src.core.service.redis_manager") as mock_r,
        patch("src.core.service.event_producer.publish", new_callable=AsyncMock) as mock_publish,
        patch("src.core.service.NotesService._call_ai") as mock_call_ai,
    ):
        mock_r.get_value = AsyncMock(return_value=None)
        mock_r.set_value = AsyncMock()
        mock_r.delete_value = AsyncMock()

        mock_call_ai.return_value = {
            "title": "Тестовый заголовок",
            "summary": "Тестовое резюме",
            "category": "Note",
        }

        yield