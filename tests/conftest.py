"""Pytest configuration and shared fixtures"""
import asyncio
import os
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Environment setup
os.environ["TESTING"] = "true"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
os.environ["TELEGRAM_SECRET_TOKEN"] = "test_secret_token"
os.environ["SENTRY_DSN"] = ""


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_redis_client():
    """Mock Redis client for testing"""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.exists = AsyncMock(return_value=False)
    return mock_client


@pytest_asyncio.fixture
async def mock_qdrant_client():
    """Mock Qdrant client for testing"""
    mock_client = AsyncMock()
    mock_client.retrieve = AsyncMock(return_value=[])
    mock_client.upsert = AsyncMock(return_value=None)
    mock_client.delete = AsyncMock(return_value=None)
    mock_client.search = AsyncMock(return_value=[])
    mock_client.collection_exists = AsyncMock(return_value=True)
    return mock_client


@pytest_asyncio.fixture
async def fastapi_app():
    """Create a FastAPI test app instance"""
    from main import app
    return app


@pytest_asyncio.fixture
async def test_client(fastapi_app) -> AsyncGenerator:
    """Create async test client"""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_client_sync(fastapi_app):
    """Create sync test client"""
    return TestClient(fastapi_app)


@pytest_asyncio.fixture
async def mock_httpx_client():
    """Mock httpx AsyncClient for API calls"""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def sample_telegram_message():
    """Sample Telegram webhook message"""
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "date": 1234567890,
            "chat": {
                "id": 987654321,
                "first_name": "Test",
                "type": "private"
            },
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test"
            },
            "text": "What's the weather?"
        }
    }


@pytest.fixture
def sample_telegram_callback():
    """Sample Telegram callback query"""
    return {
        "update_id": 123456790,
        "callback_query": {
            "id": "callback_123",
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test"
            },
            "chat_instance": "1234567890",
            "data": "btn_request",
            "message": {
                "message_id": 1,
                "chat": {
                    "id": 987654321,
                    "type": "private"
                }
            }
        }
    }
