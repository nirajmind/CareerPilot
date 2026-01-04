import os
from typing import Optional


class PromptLoader:
    def __init__(self, redis_client=None, base_path="app/gemini/prompts"):
        self.redis = redis_client
        self.base_path = base_path

    async def get(self, key: str) -> str:
        """
        Load prompt from Redis first, fallback to file.
        """
        # 1. Try Redis
        if self.redis:
            cached = await self.redis.get(f"prompt:{key}")
            if cached:
                return cached

        # 2. Fallback to file
        file_path = os.path.join(self.base_path, f"{key}.txt")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
