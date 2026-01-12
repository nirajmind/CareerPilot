import asyncio
from .logger import logger


async def retry_async(func, *args, retries=3, base_delay=0.5, **kwargs):
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
                if logger:
                    logger.error(
                        f"[GeminiService] Permanent failure after {attempt} attempts: {e}"
                    )
                raise

            # Exponential backoff + jitter
            delay = base_delay * (2 ** (attempt - 1))
            jitter = delay * 0.1
            sleep_time = delay + (jitter * (0.5 - 0.5))

            if logger:
                logger.warning(
                    f"[GeminiService] Retry {attempt}/{retries} after error: {e}. "
                    f"Sleeping {sleep_time:.2f}s"
                )

            await asyncio.sleep(sleep_time)
