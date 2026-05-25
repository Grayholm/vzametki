import pytest
from unittest.mock import AsyncMock, MagicMock

from src.ai.groq_client import GroqClient
from src.notes.repository import NotesRepository
from src.notes.service import NotesService
from src.database.qdrant_client import QdrantClient
from src.database.redis_config import RedisManager


@pytest.fixture
def mock_session():
    """Мокаем SQLAlchemy async session."""
    return AsyncMock()


@pytest.fixture
def mock_groq_client():
    """Мокаем GroqClient — не ходим в реальный API."""
    client = MagicMock(spec=GroqClient)

    async def classify_side_effect(text: str) -> dict:
        if "найди" in text.lower() or "ищи" in text.lower():
            return {"category": "Search"}
        if "покажи все" in text.lower() or "список" in text.lower():
            return {"category": "ListAll"}
        if "открой" in text.lower() or "заметку" in text.lower():
            return {"category": "GetById", "note_id": 5}
        if "привет" in text.lower() or "как дела" in text.lower():
            return {"category": "Trash"}
        return {"category": "Note"}

    async def metadata_side_effect(content: str, category: str | None = None) -> dict:
        return {
            "title": "Тестовый заголовок",
            "summary": "Тестовое краткое содержание.",
        }

    client.classify_note_content = AsyncMock(side_effect=classify_side_effect)
    client.generate_note_title_summary = AsyncMock(side_effect=metadata_side_effect)
    return client


@pytest.fixture
def mock_embedding():
    """Мокаем EmbeddingManager."""
    mock = MagicMock()
    mock.embed_text.return_value = [0.1] * 384
    return mock


@pytest.fixture
def mock_qdrant():
    """Мокаем QdrantClient."""
    client = MagicMock(spec=QdrantClient)
    client.insert_note_vector = AsyncMock()
    client.search_similar_notes = AsyncMock(return_value=[])
    client.scroll_notes_by_user_id = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_redis():
    """Мокаем RedisManager."""
    client = MagicMock(spec=RedisManager)
    client.get_value = AsyncMock(return_value=None)
    client.set_value = AsyncMock()
    client.delete_value = AsyncMock()
    return client


@pytest.fixture
def mock_notes_repo(mock_session):
    """Мокаем NotesRepository."""
    repo = MagicMock(spec=NotesRepository)
    repo.create_note = AsyncMock(return_value=1)
    repo.get_note_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def notes_service(
    mock_session,
    mock_groq_client,
    mock_embedding,
    mock_qdrant,
    mock_redis,
    mock_notes_repo,
):
    """NotesService со всеми зависимостями замокаными."""
    return NotesService(
        session=mock_session,
        repo=mock_notes_repo,
        groq_client=mock_groq_client,
        emb_client=mock_embedding,
        qdrant_client=mock_qdrant,
        redis_client=mock_redis,
    )