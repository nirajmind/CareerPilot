import pytest
import fakeredis.aioredis
from unittest.mock import MagicMock
from app.gemini.service import GeminiService


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def fake_logger():
    class DummyLogger:
        def info(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def debug(self, *args, **kwargs): pass
    return DummyLogger()


@pytest.fixture
def fake_client():
    """Mock Gemini client."""
    mock = MagicMock()
    mock.embed_content = MagicMock()
    mock.models.generate_content = MagicMock()
    mock.models.generate_content_stream = MagicMock()
    return mock


@pytest.fixture
def gemini(fake_redis, fake_logger, fake_client, monkeypatch):
    # Patch the Client inside GeminiService to use our fake client
    monkeypatch.setattr("app.gemini.service.Client", lambda api_key: fake_client)

    return GeminiService(
        redis_client=fake_redis,
        logger=fake_logger,
        embedding_ttl_seconds=60,
    )
