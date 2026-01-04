import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_retry_logic(gemini, fake_client):
    # First 2 calls fail, 3rd succeeds
    fake_client.embed_content.side_effect = [
        Exception("429 rate limit"),
        Exception("timeout"),
        MagicMock(embedding=[1, 2, 3])
    ]

    result = await gemini.embed("retry test")
    assert result == [1, 2, 3]
    assert fake_client.embed_content.call_count == 3
