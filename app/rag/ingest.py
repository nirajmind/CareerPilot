import os
from typing import Iterable, Dict, Optional
import uuid
import asyncio
from .mongo_vector import upsert
from app.gemini import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger()

gemini_client = GeminiClient()

def chunk_text(text: str, chunk_size: int = 500) -> Iterable[str]: 
    """ 
    Split text into smaller chunks (~chunk_size words) for better embedding. 
    """ 
    words = text.split() 
    if not words: 
        return [] 
    for i in range(0, len(words), chunk_size): 
        chunk = " ".join(words[i : i + chunk_size]) 
        
        logger.info(f"Created chunk length={len(chunk)}") 
        yield chunk 

async def ingest_text( 
        text: str, 
        metadata: Optional[Dict] = None, 
        chunk_size: int = 500, ) -> int: 
    """ 
    Ingest a text block into MongoDB vector store. 
    Returns number of chunks ingested. 
    """ 
    metadata = metadata or {} 
    count = 0 
    logger.info( 
        "Starting text ingestion", 
        extra={"text_len": len(text), "metadata": metadata}, 
        )
    for chunk in chunk_text(text, chunk_size=chunk_size): 
        doc_id = str(uuid.uuid4()) 
        
        logger.info(f"Generating embedding for chunk doc_id={doc_id}") 
        
        embedding = gemini_client.embed(chunk) 
        if not embedding: 
            logger.warning(f"Empty embedding for doc_id={doc_id}, skipping") 
            continue 
        
        await upsert( 
            { 
                "_id": doc_id, 
                "text": chunk, 
                "embedding": embedding, 
                "metadata": metadata, 
                } 
                ) 
        count += 1 
        logger.info(f"Completed text ingestion chunks_ingested={count}") 
        return count 
    
async def ingest_file( 
    filepath: str, 
    metadata: Optional[Dict] = None, 
    chunk_size: int = 500, 
    ) -> int: 
    """ 
    Ingest a single text file into the vector store. 
    Returns number of chunks ingested. 
    """ 
    if not os.path.exists(filepath): 
        raise FileNotFoundError(f"File not found: {filepath}") 
    
    logger.info(f"Reading file for ingestion filepath={filepath}") 
    
    with open(filepath, "r", encoding="utf-8") as f: 
        content = f.read() 
    effective_metadata = {"source": filepath} 
    if metadata: 
        effective_metadata.update(metadata) 

    return await ingest_text( 
        content, metadata=effective_metadata, chunk_size=chunk_size, 
        ) 
    
async def ingest_directory( 
        dirpath: str, 
        glob_ext: Optional[str] = ".txt", 
        chunk_size: int = 500, 
        ) -> int: 
    """ 
    Ingest all files in a directory (optionally filtered by extension). 
    Returns total chunks ingested. 
    """ 
    if not os.path.isdir(dirpath): 
        raise NotADirectoryError(f"Not a directory: {dirpath}") 
    
    logger.info(f"Starting directory ingestion dirpath={dirpath} ext={glob_ext}") 
    
    total_chunks = 0 
    for entry in os.scandir(dirpath): 
        if not entry.is_file(): 
            continue 
        if glob_ext and not entry.name.endswith(glob_ext): 
            continue 
        
        try: 
            chunks = await ingest_file( 
                entry.path, 
                metadata={"source_dir": dirpath}, 
                chunk_size=chunk_size, 
                ) 
            total_chunks += chunks 
        except Exception as e: 
            logger.exception(f"Failed to ingest file path={entry.path} error={e}")

        logger.info( "Completed directory ingestion", 
                    extra={"dirpath": dirpath, "total_chunks": total_chunks}, 
                ) 
        return total_chunks

PENDING_DIR = "/app/data/pending" 

async def ingest_pending_files(): 
    for filename in os.listdir(PENDING_DIR): 
        filepath = os.path.join(PENDING_DIR, filename) 
        if not os.path.isfile(filepath): 
            continue 
        logger.info(f"Ingesting pending file: {filepath}")
        await ingest_file(filepath) 
        os.remove(filepath)