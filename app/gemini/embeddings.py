import json
import hashlib
from .logger import logger
from .json_utils import safe_json_parse


async def embed(client, text: str):
    if not text or not text.strip():
        logger.warning("embed() called with empty text")
        return []

    key = _cache_key(client.embedding_model, text)

    # Try Redis cache
    if client.redis:
        try:
            cached = await client.redis.get(key)
            if cached:
                embedding = safe_json_parse(cached)
                if embedding:
                    logger.info("Embedding cache hit", extra={"key": key})
                    return embedding
        except Exception as e:
            logger.exception(f"Redis read failed for key={key}: {e}")

    logger.info("Calling Gemini for embedding", extra={"key": key})
    logger.debug(f"Embedding input text: {text}")

    embedding = []

    try:
        payload = {
            "content": {
                "parts": [{"text": text}]
            }
        }

        resp = await client.call(
            "embedding",
            f"models/{client.embedding_model}:embedContent",
            payload
        )

        embedding = resp["embedding"]["values"]

    except Exception as e:
        logger.exception(f"Gemini embedding call failed: {e}")
        return []

    # Cache embedding
    if client.redis:
        try:
            await client.redis.set(key, json.dumps(embedding))
        except Exception as e:
            logger.exception(f"Redis write failed for key={key}: {e}")

    return embedding


def _cache_key(model: str, text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"emb:{model}:{h}"
