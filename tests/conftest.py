from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.repository import NotesRepository
from src.core.service import NotesService
from src.infrastructure.redis import RedisManager


@pytest.fixture
def mock_session():
    """Мокаем SQLAlchemy async session."""
    return AsyncMock()


@pytest.fixture
def mock_notes_repo(mock_session):
    """Мокаем NotesRepository."""
    repo = MagicMock(spec=NotesRepository)
    repo.create_note = AsyncMock(return_value=1)
    repo.get_note_by_id = AsyncMock(return_value=None)
    repo.update_note = AsyncMock()
    repo.delete_note = AsyncMock()
    return repo


@pytest.fixture
def mock_redis():
    """Мокаем RedisManager."""
    client = MagicMock(spec=RedisManager)
    client.get_value = AsyncMock(return_value=None)
    client.set_value = AsyncMock()
    client.delete_value = AsyncMock()
    client.ping = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def notes_service(mock_session, mock_notes_repo):
    """NotesService с замоканными зависимостями."""
    return NotesService(session=mock_session, repo=mock_notes_repo)