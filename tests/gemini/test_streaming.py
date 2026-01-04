import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_streaming(gemini, fake_client):
    # Fake streaming chunks
    fake_client.models.generate_content_stream.return_value = [
        MagicMock(text="Hello "),
        MagicMock(text="World"),
    ]

    chunks = []
    async for c in gemini.stream_answer("test prompt"):
        chunks.append(c)

    assert chunks == ["Hello ", "World"]
