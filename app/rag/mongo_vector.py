from pymongo import MongoClient
from pymongo.collection import Collection
from typing import List, Dict
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = "careerpilot"
COLLECTION_NAME = "vectors"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection: Collection = db[COLLECTION_NAME]


def upsert_document(doc_id: str, text: str, embedding: List[float], metadata: Dict = None):
    """Insert or update a document with its embedding."""
    payload = {
        "_id": doc_id,
        "text": text,
        "embedding": embedding,
        "metadata": metadata or {}
    }
    collection.update_one({"_id": doc_id}, {"$set": payload}, upsert=True)


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