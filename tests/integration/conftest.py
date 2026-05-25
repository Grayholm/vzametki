import pytest

from src.database.config import settings
from src.database.db import Base, engine


@pytest.fixture(scope="session", autouse=True)
async def check_test_mode():
    assert settings.MODE == "test", f"MODE must be 'test', got '{settings.MODE}'"


@pytest.fixture(scope="session", autouse=True)
async def setup_database(check_test_mode):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)