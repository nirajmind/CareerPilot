import asyncio
from .ingest import ingest_file
from time import sleep
from app.utils.logger import setup_logger

logger = setup_logger()

async def main():
    while True:
        logger.info("Agent is running. No ingestion source configured yet.")
        await asyncio.sleep(5)
        sleep(2)

if __name__ == "__main__":
    logger.info("Starting pending file ingestion service...")
    asyncio.run(main())
