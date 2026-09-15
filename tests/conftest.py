import asyncio
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth import require_user
from app.db.session import get_db
from app.main import app
from app.storage.dependencies import get_storage
from tests.settings import test_settings


class FakeStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def upload(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        self.files[key] = content

    async def download(
        self,
        *,
        key: str,
    ) -> bytes:
        return self.files[key]

    async def delete(
        self,
        *,
        key: str,
    ) -> None:
        self.files.pop(key, None)

@pytest.fixture
def fake_storage():
    return FakeStorage()

def pytest_asyncio_loop_factories(config, item):
    if sys.platform == "win32":
        return {
            "selector": asyncio.SelectorEventLoop,
        }

    return {
        "default": asyncio.new_event_loop,
    }


test_engine = create_async_engine(
    test_settings.database_url,
    poolclass=NullPool,
)


@pytest_asyncio.fixture
async def db_session():
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
def auth_user():
    return {
        "user_id": "user_test_123",
    }


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    auth_user,
    fake_storage,
):
    async def override_get_db():
        yield db_session

    async def override_require_user():
        return auth_user["user_id"]
    
    def override_get_storage():
        return fake_storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_user] = override_require_user
    app.dependency_overrides[get_storage] = override_get_storage
    
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.clear()