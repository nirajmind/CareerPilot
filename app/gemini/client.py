import os
import uuid
import time
import httpx
import json

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
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "v1/models/text-embedding-004")

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

            if result.status_code != 200:
                logger.error(f"[Gemini:{operation}] Failed with status {result.status_code}")
                logger.error(f"[Gemini:{operation}] Response body: {result.text}")
                result.raise_for_status()

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

    async def call_stream(self, operation, model, payload):
        """
        Streaming version of call method.
        Yields decoded JSON chunks from the Gemini stream.
        """
        cid = self.new_correlation_id()
        logger.info(f"[Gemini] Start Stream {operation} cid={cid}")
        
        # Ensure we hit the streaming endpoint if not specified
        if "generateContent" in model and "stream" not in model:
             model = model.replace("generateContent", "streamGenerateContent")
        
        url = f"{self.proxy_base}/{model}"
        logger.info(f"[Gemini] Stream URL = {url}")
        
        headers = {
            "Content-Type": "application/json",
            "x-careerpilot": self.proxy_secret
        }

        async with self.http.stream("POST", url, json=payload, headers=headers, timeout=60) as response:
            if response.status_code != 200:
                error_body = await response.read()
                logger.error(f"[Gemini:Stream] Failed status={response.status_code} body={error_body}")
                raise Exception(f"Gemini streaming failed: {response.status_code}")
                
            decoder = json.JSONDecoder()
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while buffer:
                    # Skip common array delimiters to parse individual JSON objects
                    s_buffer = buffer.lstrip().lstrip(',').lstrip('[').lstrip()
                    if not s_buffer:
                        # If we stripped everything but still have data in original buffer (like a trailing comma/bracket at very end of stream), 
                        # we might need to be careful. But usually lstrip handles it.
                        # If s_buffer is empty, we break to get more data or finish.
                        # Note: We must NOT discard 'buffer' if s_buffer is empty due to lack of data (incomplete token).
                        # But lstrip() only removes whitespace/chars. It doesn't fail on partials.
                        # However, if buffer is just "]", s_buffer becomes empty.
                        if "]" in buffer and not s_buffer: 
                            # End of array
                            buffer = ""
                        break
                    
                    try:
                        obj, idx = decoder.raw_decode(s_buffer)
                        yield obj
                        # Move buffer forward
                        # We need to calculate how much we stripped + idx
                        # This is tricky with lstrip.
                        # Safer approach:
                        stripped_count = len(buffer) - len(s_buffer)
                        buffer = buffer[stripped_count + idx:]
                    except json.JSONDecodeError:
                        # Incomplete JSON, wait for more chunks
                        break
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
