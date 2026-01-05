import asyncio
from pymongo import MongoClient
from typing import List, Dict
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = "careerpilot"
COLLECTION_NAME = "vectors"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def upsert(document: Dict):
    """Insert or update a document with its embedding asynchronously."""
    doc_id = document.get("text")
    def sync_upsert():
        return collection.update_one(
            {"_id": doc_id},
            {"$set": document},
            upsert=True
        )
    return await asyncio.to_thread(sync_upsert)

def search(query_embedding: List[float], top_k: int = 5):
    """Perform vector search using cosine similarity."""
    pipeline = [
        {
            "$vectorSearch": {
                "queryVector": query_embedding,
                "path": "embedding",
                "numCandidates": 50,
                "limit": top_k,
                "index": "vector_index"
            }
        },
        {
            "$project": {
                "text": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    return list(collection.aggregate(pipeline))