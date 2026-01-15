import asyncio
import time
from typing import List, Dict, Any
from bson import ObjectId
from pymongo import MongoClient
import os
from app.utils.logger import setup_logger

logger = setup_logger()

# -------------------------------------------------------------------
# MongoDB Setup
# -------------------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/careerpilot")
DB_NAME = os.getenv("MONGO_DB", "careerpilot")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "vectors")

_client = MongoClient(MONGO_URI)
_db = _client[DB_NAME]
_collection = _db[COLLECTION_NAME]


# -------------------------------------------------------------------
# Upsert Document
# -------------------------------------------------------------------
async def upsert(document: Dict[str, Any]):
    """
    Insert or update a document with its embedding asynchronously.
    Ensures `_id` exists. Adds rich logging for debugging.
    """

    # Ensure _id exists
    if "_id" not in document:
        generated_id = str(ObjectId())
        document["_id"] = generated_id
        logger.warning(
            "Document missing _id — generated new one",
            extra={"generated_id": generated_id, "metadata": document.get("metadata")}
        )

    doc_id = document["_id"]

    # Validate embedding
    embedding = document.get("embedding")
    if embedding is None:
        logger.error(
            "Document missing embedding — cannot upsert",
            extra={"doc_id": doc_id, "document": document}
        )
        raise ValueError("Document missing embedding")

    # Log ingestion details
    logger.info(
        "Upserting vector document",
        extra={
            "doc_id": doc_id,
            "text_len": len(document.get("text", "")),
            "embedding_dims": len(embedding),
            "has_metadata": bool(document.get("metadata")),
            "metadata": document.get("metadata"),
        },
    )

    start = time.time()

    def sync_upsert():
        return _collection.update_one(
            {"_id": doc_id},
            {"$set": document},
            upsert=True,
        )

    try:
        result = await asyncio.to_thread(sync_upsert)
    except Exception as e:
        logger.exception(
            "MongoDB upsert failed",
            extra={"doc_id": doc_id, "error": str(e), "document": document},
        )
        raise

    duration = round((time.time() - start) * 1000, 2)

    # Log result
    if result.upserted_id:
        logger.info(
            "Inserted new vector document",
            extra={"doc_id": doc_id, "duration_ms": duration},
        )
    else:
        logger.info(
            "Updated existing vector document",
            extra={"doc_id": doc_id, "duration_ms": duration},
        )

    return result


# -------------------------------------------------------------------
# Vector Search
# -------------------------------------------------------------------
async def search(query_embedding: List[float], top_k: int = 5):
    """
    Perform vector search using MongoDB Atlas Vector Search.
    Includes detailed logging and timing.
    """

    logger.info(
        "Running vector search",
        extra={
            "top_k": top_k,
            "embedding_dims": len(query_embedding),
        },
    )

    pipeline = [
        {
            "$vectorSearch": {
                "queryVector": query_embedding,
                "path": "embedding",
                "numCandidates": 50,
                "limit": top_k,
                "index": "vector_index",
            }
        },
        {
            "$project": {
                "text": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    start = time.time()

    def sync_search():
        return list(_collection.aggregate(pipeline))

    try:
        results = await asyncio.to_thread(sync_search)
    except Exception as e:
        logger.exception(
            "Vector search failed",
            extra={"error": str(e), "pipeline": pipeline},
        )
        raise

    duration = round((time.time() - start) * 1000, 2)

    logger.info(
        "Vector search completed",
        extra={
            "result_count": len(results),
            "duration_ms": duration,
            "top_scores": [r.get("score") for r in results[:3]],
        },
    )

    return results
