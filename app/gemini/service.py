import os
import asyncio
import hashlib
import json
import re
from typing import List, Optional
from google.genai import Client
from app.gemini.prompt_loader import PromptLoader
import uuid
import time

from app.utils.logger import setup_logger
logger = setup_logger()

class GeminiService:
    def __init__( self, redis_client=None, logger=None, 
                 embedding_ttl_seconds: int = 60 * 60 * 24 * 30, # 30 days 
                 ):
             api_key = os.getenv("GEMINI_API_KEY") 
             if not api_key: 
                 raise ValueError("GEMINI_API_KEY is missing") 
             # Async Gemini client 
             self.client = Client(api_key=api_key).aio 
             self.embedding_model = "models/text-embedding-004" 
             self.chat_model = "models/gemini-2.0-flash" 
             self.redis = redis_client 
             self.logger = logger or logger
             self.emb_ttl = embedding_ttl_seconds 
             self.prompts = PromptLoader(redis_client)

    def _new_correlation_id(self):
        return str(uuid.uuid4())

    async def _log_and_time(self, operation: str, func, *args, **kwargs):
        """
        Wraps a Gemini call with:
        - correlation ID
        - timing
        - structured logs
        """
        cid = self._new_correlation_id()
        start = time.time()

        if self.logger:
            self.logger.info({
                "event": "gemini_call_start",
                "operation": operation,
                "correlation_id": cid,
                "args": str(args),
                "kwargs": str(kwargs),
            })

        try:
            result = await self._retry(func, *args, **kwargs)
            duration = time.time() - start

            if self.logger:
                self.logger.info({
                    "event": "gemini_call_success",
                    "operation": operation,
                    "correlation_id": cid,
                    "duration_ms": int(duration * 1000),
                })

            return result

        except Exception as e:
            duration = time.time() - start

            if self.logger:
                self.logger.error({
                    "event": "gemini_call_failure",
                    "operation": operation,
                    "correlation_id": cid,
                    "duration_ms": int(duration * 1000),
                    "error": str(e),
                })

            raise
 
    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ---------------------------------------------------------
    # EMBEDDINGS
    # ---------------------------------------------------------
    async def embed(self, text: str) -> List[float]:
        if not text or not text.strip():
            return []

        cache_key = self._embedding_cache_key(text)

        # 1. Try Redis cache first
        if self.redis is not None:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    embedding = json.loads(cached)
                    if self.logger:
                        self.logger.info(f"[GeminiService] Embedding cache HIT for key={cache_key}")
                    return embedding
                else:
                    if self.logger:
                        self.logger.info(f"[GeminiService] Embedding cache MISS for key={cache_key}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"[GeminiService] Redis error on GET {cache_key}: {e}")

        # 2. No cache → generate embedding via Gemini
        prompt_template = await self.prompts.get("rag_embedding")
        prompt = prompt_template.format(query=text)

        resp = await self._log_and_time(
            "embed_content",
            self.client.embed_content,
            model=self.embedding_model,
            content=prompt,
            task_type="retrieval_document",
        )

        embedding = resp.embedding

        # 3. Store in Redis for future reuse
        if self.redis is not None:
            try:
                await self.redis.set(
                    cache_key,
                    json.dumps(embedding),
                    ex=self.emb_ttl,
                )
                if self.logger:
                    self.logger.info(f"[GeminiService] Embedding cached for key={cache_key} ttl={self.emb_ttl}s")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"[GeminiService] Redis error on SET {cache_key}: {e}")

        return embedding


    # ---------------------------------------------------------
    # RESUME + JD ANALYSIS
    # ---------------------------------------------------------
    async def analyze_resume_and_jd(self, resume: str, jd: str) -> str:
        logger.info(f"Starting resume and JD analysis with prompt.")
        prompt_template = await self.prompts.get("analyze_resume")
        logger.info(
            f"Loaded prompt template for resume analysis. "
            f"prompt_preview={prompt_template[:100]}"
        )

        prompt = prompt_template.replace("{resume}", resume).replace("{jd}", jd)

        resp = await self._log_and_time(
            "generate_content_resume_analysis",
            self.client.models.generate_content,
            model=self.chat_model,
            contents=prompt,
        )
        logger.info(f"The raw response from gemini - {resp}")
        text = resp.candidates[0].content.parts[0].text
        return self.safe_json_parse(text)

    # ---------------------------------------------------------
    # ANSWER EVALUATION
    # ---------------------------------------------------------
    async def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        resume_text: str,
        jd_text: str,
    ) -> str:

        prompt_template = await self.prompts.get("evaluate_answer")

        prompt = prompt_template.format(
            question=question,
            answer=user_answer,
            resume=resume_text,
            jd=jd_text,
        )

        resp = await self._log_and_time(
            "generate_content_answer_evaluation",
            self.client.models.generate_content,
            model=self.chat_model,
            contents=prompt,
        )

        return self.safe_json_parse(resp.text)
    
    def _embedding_cache_key(self, text: str) -> str:
        """
        Generate a stable Redis key for an embedding query.
        Includes model name to avoid cross-model collisions.
        """
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self.embedding_model}:{h}"
    
    async def _retry(self, func, *args, retries=3, base_delay=0.5, **kwargs):
        """
        Retry wrapper with exponential backoff + jitter.
        Retries only on safe transient errors.
        """
        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                # Retry only on transient errors
                transient = (
                    "429" in str(e) or
                    "rate" in str(e).lower() or
                    "timeout" in str(e).lower() or
                    "unavailable" in str(e).lower() or
                    "500" in str(e)
                )

                if not transient or attempt == retries:
                    if self.logger:
                        self.logger.error(
                            f"[GeminiService] Permanent failure after {attempt} attempts: {e}"
                        )
                    raise

                # Exponential backoff + jitter
                delay = base_delay * (2 ** (attempt - 1))
                jitter = delay * 0.1
                sleep_time = delay + (jitter * (0.5 - 0.5))

                if self.logger:
                    self.logger.warning(
                        f"[GeminiService] Retry {attempt}/{retries} after error: {e}. "
                        f"Sleeping {sleep_time:.2f}s"
                    )

                await asyncio.sleep(sleep_time)

    def safe_json_parse(self, text: str):
        """
        Attempts to parse JSON from LLM output safely.
        - Handles markdown fences
        - Extracts JSON substring
        - Repairs common formatting issues
        - Logs failures
        """
        # 1. Direct strict parse
        try:
            return json.loads(text)
        except Exception:
            logger.error(f"[GeminiService] Failed to parse JSON from response - {text}")
            pass

        # 2. Remove markdown fences
        cleaned = re.sub(r"```json\s*|```\s*", "", text, flags=re.MULTILINE).strip()
        logger.info(f"[GeminiService] Parsing JSON from cleaned response - {cleaned}")
        try:
            return json.loads(cleaned)
        except Exception:
            logger.error(f"[GeminiService] Failed to parse JSON from cleaned response - {cleaned}")
            pass

        # 3. Extract JSON substring using regex
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except Exception:
                logger.error(f"[GeminiService] Failed to parse JSON from match response - {json_match.group(0)}")
                pass

        # 4. Attempt common repairs
        repaired = (
            cleaned.replace("\n", " ")
            .replace(",}", "}")
            .replace(",]", "]")
        )
        logger.info(f"[GeminiService] Parsing JSON from repaired response - {repaired}")
        try:
            return json.loads(repaired)
        except Exception as e:
            logger.error(f"[GeminiService] Failed to parse JSON: {e}")
            logger.error(f"[GeminiService] Failed to parse JSON from response - {repaired}")
            pass

        # 5. Final fallback: return raw text
        if self.logger:
            self.logger.warning(f"[GeminiService] Failed to parse JSON. Returning raw text.")

        logger.info(f"[GeminiService] Parsed json from response - {text}")
        return {"raw_text": text}
    
    async def stream_answer(self, prompt: str):
        cid = self._new_correlation_id() 

        if self.logger: 
            self.logger.info({ "event": "gemini_stream_start", "correlation_id": cid, })
        """
        Async generator that streams Gemini output chunk-by-chunk.
        """
        try:
            stream = self.client.models.generate_content_stream(
                model=self.chat_model,
                contents=prompt,
            )

            # Iterate over streaming chunks in a thread executor
            loop = asyncio.get_event_loop()
            iterator = await loop.run_in_executor(None, lambda: stream)

            for chunk in iterator:
                text = chunk.text or ""
                if self.logger:
                    self.logger.debug({ "event": "gemini_stream_chunk", "correlation_id": cid, "chunk_preview": text[:50], })
                yield text

            if self.logger: 
                self.logger.info({ "event": "gemini_stream_end", "correlation_id": cid, })    

        except Exception as e:
            if self.logger: 
                self.logger.error({ "event": "gemini_stream_error", "correlation_id": cid, "error": str(e), })
            yield f"[ERROR] {str(e)}"

    async def stream_resume_analysis(self, resume: str, jd: str):
        prompt_template = await self.prompts.get("analyze_resume")
        prompt = prompt_template.format(resume=resume, jd=jd)
        async for chunk in self.stream_answer(prompt):
            yield chunk

    async def stream_evaluation(self, question: str, answer: str, resume: str, jd: str):
        prompt_template = await self.prompts.get("evaluate_answer")
        prompt = prompt_template.format(
            question=question,
            answer=answer,
            resume=resume,
            jd=jd,
        )
        async for chunk in self.stream_answer(prompt):
            yield chunk
        
        
