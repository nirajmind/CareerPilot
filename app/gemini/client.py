from cProfile import label
import os
import uuid
import time
from google.genai import Client
from google.genai.types import HarmCategory, HarmBlockThreshold

from app.gemini.prompt_loader import PromptLoader

from .retry import retry_async
from .logger import logger


class GeminiClient:
    def __init__(self, redis_client=None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        self.redis = redis_client
        self.client = Client(api_key=api_key).aio

        self.prompts = PromptLoader(redis_client)
        
        self.chat_model = os.getenv("GEMINI_MODEL", "models/gemini-pro")
        self.vision_model = os.getenv("GEMINI_VISION_MODEL", "models/gemini-pro-vision")
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")

    def new_correlation_id(self):
        return str(uuid.uuid4())

    async def call(self, operation, func, *args, **kwargs):
        cid = self.new_correlation_id()
        start = time.time()

        logger.info(f"[Gemini] Start {operation} cid={cid}")

        try:
            logger.info(f"[Gemini:{operation}] Request started") 
            logger.debug(f"[Gemini:{operation}] Payload keys: {list(kwargs.keys())}")
            result = await retry_async(func, *args, **kwargs)
            logger.info(f"[Gemini] Success {operation} cid={cid} duration={int((time.time()-start)*1000)}ms")
            return result
        except Exception as e:
            logger.error(f"[Gemini:{operation}] Request failed") 
            logger.error(f"[Gemini:{operation}] Exception type: {type(e)}") 
            logger.error(f"[Gemini:{operation}] Exception message: {str(e)}")
            logger.error(f"[Gemini] Failure {operation} cid={cid} error={e}")
            if hasattr(e, "response"): 
                logger.error(f"[Gemini:{operation}] Gemini response: {e.response}")
            raise

    def safety(self):
        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
