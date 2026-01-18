import argparse
import asyncio
import logging
import os
from typing import Optional

from app.utils.logger import setup_logger

logger = setup_logger()
from app.rag.ingest import ingest_file, ingest_directory, ingest_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CareerPilot RAG ingestion CLI")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Path to a single text file to ingest")
    group.add_argument("--dir", type=str, help="Path to a directory of text files")
    group.add_argument(
        "--text",
        type=str,
        help="Raw text to ingest (for quick tests; not for large content)",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Approximate number of words per chunk",
    )

    parser.add_argument(
        "--ext",
        type=str,
        default=".txt",
        help="File extension filter for directory ingestion (e.g. .txt)",
    )

    return parser.parse_args()


async def _run(
    file: Optional[str],
    dir: Optional[str],
    text: Optional[str],
    chunk_size: int,
    ext: str,
):
    if file:
        logger.info(f"CLI ingestion: file={file}")
        chunks = await ingest_file(file, chunk_size=chunk_size)
        logger.info(f"File ingestion complete file={file} chunks={chunks}")

    elif dir:
        logger.info(f"CLI ingestion: dir={dir} ext={ext}")
        chunks = await ingest_directory(dir, glob_ext=ext, chunk_size=chunk_size)
        logger.info(f"Directory ingestion complete dir={dir} total_chunks={chunks}")

    elif text:
        logger.info("CLI ingestion: raw text")
        chunks = await ingest_text(text, chunk_size=chunk_size)
        logger.info(f"Text ingestion complete chunks={chunks}")


def main():
    # Basic logging safety (in case app.utils.logger isn't wired)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    args = parse_args()

    asyncio.run(
        _run(
            file=args.file,
            dir=args.dir,
            text=args.text,
            chunk_size=args.chunk_size,
            ext=args.ext,
        )
    )


if __name__ == "__main__":
    main()
