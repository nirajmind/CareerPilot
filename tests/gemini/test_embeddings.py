import pytest
import json

@pytest.mark.asyncio
async def test_embedding_cache(gemini, fake_redis, fake_client):
    # Fake embedding response
    fake_client.embed_content.return_value.embedding = [0.1, 0.2, 0.3]

    text = "hello world"

    # First call → cache miss → Gemini called
    emb1 = await gemini.embed(text)
    assert emb1 == [0.1, 0.2, 0.3]
    fake_client.embed_content.assert_called_once()

    # Second call → cache hit → Gemini NOT called again
    emb2 = await gemini.embed(text)
    assert emb2 == [0.1, 0.2, 0.3]
    assert fake_client.embed_content.call_count == 1  # still 1
