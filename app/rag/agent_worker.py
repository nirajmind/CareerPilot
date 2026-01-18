import asyncio
from app.rag.ingest import ingest_pending_files  # you will define this later
from app.utils.logger import setup_logger

logger = setup_logger()
async def main():
    logger.info("Agent worker started. Waiting for ingestion tasks...")

    while True:
        try:
            # This function should check for pending ingestion tasks
            # (Redis queue, Mongo queue, folder watcher, etc.)
            await ingest_pending_files()
        except Exception as e:
            logger.exception(f"Error in agent loop: {e}")

        await asyncio.sleep(5)  # prevent tight loop

if __name__ == "__main__":
    asyncio.run(main())
