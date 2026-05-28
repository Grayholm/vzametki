from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401
import pytest
import pytest_asyncio

from src.notes.models import NotesModel # noqa: F401
from src.main import app  # noqa: F401

from src.database.db import Base, engine_null_pool


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Дропаем и создаём таблицы один раз за всю сессию."""
    async with engine_null_pool.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="session")
async def ac():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    
@pytest.fixture(autouse=True)
def _mocks():
    """Мокаем Groq, Qdrant, Redis, Embedding — тестируем только API → сервис → БД."""
    with (
        patch("src.database.qdrant_client") as mock_q,
        patch("src.database.redis_config") as mock_r,
        patch("src.database.embedding") as mock_emb,
        patch("src.ai.groq_client.GroqClient.classify_note_content") as mock_classify,
        patch("src.ai.groq_client.GroqClient.generate_note_title_summary") as mock_metadata,
    ):
        mock_q.insert_note_vector = AsyncMock()
        mock_q.delete_note_vector = AsyncMock()
        mock_q.search_similar_notes = AsyncMock(return_value=[])
        mock_q.scroll_notes_by_user_id = AsyncMock(return_value=[])
        mock_r.get_value = AsyncMock(return_value=None)
        mock_r.set_value = AsyncMock()
        mock_r.delete_value = AsyncMock()

        mock_emb_instance = MagicMock()
        mock_emb_instance.embed_text = MagicMock(return_value=[0.1] * 384)
        mock_emb.return_value = mock_emb_instance

        mock_classify.return_value = {"category": "Note"}
        mock_metadata.return_value = {
            "title": "Тестовый заголовок",
            "summary": "Тестовое резюме",
        }

        yield
