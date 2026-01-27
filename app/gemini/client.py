import os
import uuid
import time
import httpx

from app.gemini.prompt_loader import PromptLoader
from .retry import retry_async
from .logger import logger


class GeminiClient:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.prompts = PromptLoader(redis_client)

        # Cloud Run proxy URL
        self.proxy_base = os.getenv("GEMINI_PROXY_URL")
        if not self.proxy_base:
            raise ValueError("GEMINI_PROXY_URL is missing")

        # Shared secret for proxy authentication
        self.proxy_secret = os.getenv("PROXY_SECRET")
        if not self.proxy_secret:
            raise ValueError("PROXY_SECRET is missing")

        # Model names
        self.chat_model = os.getenv("GEMINI_MODEL", "models/gemini-pro")
        self.vision_model = os.getenv("GEMINI_VISION_MODEL", "models/gemini-pro-vision")
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")

        # HTTP client
        self.http = httpx.AsyncClient(timeout=60)

    def new_correlation_id(self):
        return str(uuid.uuid4())

    def safety(self):
        # Keep your existing safety config untouched
        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    async def call(self, operation, model, payload):
        """
        Generic method to call Gemini through the Cloud Run proxy.
        Uses retry_async exactly as before.
        """
        cid = self.new_correlation_id()
        start = time.time()

        logger.info(f"[Gemini] Start {operation} cid={cid}")
        logger.debug(f"[Gemini:{operation}] Payload keys: {list(payload.keys())}")

        url = f"{self.proxy_base}/{model}"
        logger.info(f"[Gemini] Final URL = {url}")

        headers = {
            "Content-Type": "application/json",
            "x-careerpilot": self.proxy_secret
        }

        try:
            result = await retry_async(
                self.http.post,
                url,
                json=payload,
                headers=headers
            )

            logger.info(
                f"[Gemini] Success {operation} cid={cid} "
                f"duration={int((time.time()-start)*1000)}ms"
            )
            return result.json()

        except Exception as e:
            logger.error(f"[Gemini:{operation}] Request failed")
            logger.error(f"[Gemini:{operation}] Exception type: {type(e)}")
            logger.error(f"[Gemini:{operation}] Exception message: {str(e)}")

            if hasattr(e, "response"):
                logger.error(f"[Gemini:{operation}] Proxy/Gemini response: {e.response.text}")

            raise

    # -----------------------------
    # High-level API wrappers
    # -----------------------------

    async def generate_text(self, text):
        payload = {
            "contents": [
                {
                    "parts": [{"text": text}]
                }
            ]
        }
        return await self.call("generate_text", f"{self.chat_model}:generateContent", payload)

    async def generate_vision(self, image_bytes, prompt="Describe this image"):
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}}
                    ]
                }
            ]
        }
        return await self.call("vision", f"{self.vision_model}:generateContent", payload)

    async def embed_text(self, text):
        payload = {
            "content": {"parts": [{"text": text}]}
        }
        return await self.call("embedding", f"{self.embedding_model}:embedContent", payload)
