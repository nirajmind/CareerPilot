import json
import hashlib
from .json_utils import safe_json_parse
from .logger import logger


async def embed(client, text: str):
    if not text.strip():
        return []

    key = _cache_key(client.embedding_model, text)

    if client.redis:
        cached = await client.redis.get(key)
        if cached:
            return json.loads(cached)

    prompt = f"Embed this text:\n{text}"

    resp = await client.call(
        "embed",
        client.client.embed_content,
        model=client.embedding_model,
        content=prompt,
        task_type="retrieval_document",
    )

    embedding = resp.embedding

    if client.redis:
        await client.redis.set(key, json.dumps(embedding))

    return embedding


def _cache_key(model, text):
    h = hashlib.sha256(text.encode()).hexdigest()
    return f"emb:{model}:{h}"
