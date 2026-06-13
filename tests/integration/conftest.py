from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from services.notes_service.src.core.models import NotesModel  # noqa: F401
from services.api_gateway.src.main import app
from services.notes_services.src.infrastructure.db import Base, engine_null_pool, async_session_maker_null_pool
from services.notes_service.src.core.service import NotesService
from services.notes_services.src.api.routers import get_notes_service


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
    async def _override_get_notes_service():
        return NotesService(session=db_session)

    app.dependency_overrides[get_notes_service] = _override_get_notes_service

    transport = ASGITransport(app=app) 
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mocks():
    """Мокаем внешние сервисы — тестируем только API → сервис → БД."""
    with (
        patch("src.notes.service.default_qdrant_client") as mock_q,
        patch("src.notes.service.default_redis_manager") as mock_r,
        patch("src.notes.service.EmbeddingManager") as mock_emb,
        patch("src.notes.service.GroqClient") as mock_groq,
    ):
        mock_q.insert_note_vector = AsyncMock()
        mock_q.delete_note_vector = AsyncMock()
        mock_q.search_similar_notes = AsyncMock(return_value=[])
        mock_q.scroll_notes_by_user_id = AsyncMock(return_value=[])

        mock_r.get_value = AsyncMock(return_value=None)
        mock_r.set_value = AsyncMock()
        mock_r.delete_value = AsyncMock()

        emb_instance = MagicMock()
        emb_instance.embed_text = MagicMock(return_value=[0.1] * 384)
        mock_emb.return_value = emb_instance

        groq_instance = MagicMock()
        groq_instance.classify_note_content = AsyncMock(return_value={"category": "Note"})
        groq_instance.generate_note_title_summary = AsyncMock(return_value={
            "title": "Тестовый заголовок",
            "summary": "Тестовое резюме",
        })
        mock_groq.return_value = groq_instance

        yield