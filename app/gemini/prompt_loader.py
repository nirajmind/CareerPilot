import asyncio
import os
from typing import Optional
import redis.asyncio as redis

from app.utils.logger import setup_logger
logger = setup_logger()

redis_client = redis.Redis(
    host="redis", port=6379, 
    decode_responses=True
)

class PromptLoader:
    def __init__(self, redis_client=None, base_path="app/gemini/prompts"):
        self.redis = redis_client
        self.base_path = base_path

    async def get(self, key: str) -> str:
        logger.info(f"Loading prompt for key={key}")

        # 1. Try Redis only if async client
        if self.redis and asyncio.iscoroutinefunction(self.redis.get):
            try:
                cached = await self.redis.get(f"prompt:{key}")
                if cached:
                    return cached
            except Exception as e:
                logger.error(f"Redis error while loading prompt {key}: {e}")

        # 2. Fallback to file
        file_path = os.path.join(self.base_path, f"{key}.txt")
        logger.info(f"Loading prompt from file: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()