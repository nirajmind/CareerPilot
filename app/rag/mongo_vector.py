import asyncio
from pymongo import MongoClient
from typing import List, Dict
import os
from app.utils.logger import setup_logger

logger = setup_logger()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/careerpilot") 
DB_NAME = os.getenv("MONGO_DB", "careerpilot") 
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "vectors") 
_client = MongoClient(MONGO_URI) 
_db = _client[DB_NAME] 
_collection = _db[COLLECTION_NAME] 
async def upsert(document: Dict): 
    """ 
    Insert or update a document with its embedding asynchronously. 
    Uses document['_id'] as stable identifier. 
    """ 
    doc_id = document["_id"] 
    logger.info( "Upserting document", 
                extra={ 
                    "doc_id": doc_id, 
                    "text_len": len(document.get("text", "")), 
                    "has_embedding": bool(document.get("embedding")), 
                    "metadata": document.get("metadata"), 
                    }, 
                ) 
    def sync_upsert(): 
        return _collection.update_one( 
            {"_id": doc_id}, 
            {"$set": document}, 
            upsert=True, 
        ) 
    result = await asyncio.to_thread(sync_upsert) 
    
    if result.upserted_id: 
        logger.info(f"Inserted new vector doc_id={doc_id}") 
    else: 
        logger.info(f"Updated existing vector doc_id={doc_id}") 
    
    return result 

async def search(query_embedding: List[float], top_k: int = 5): 
    """ 
    Perform vector search using MongoDB Atlas Vector Search. 
    Assumes a 'vector_index' exists on field 'embedding'. 
    """ 
    
    logger.info(f"Running vector search top_k={top_k}") 
    
    pipeline = [ { 
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
                    "score": {
                        "$meta": "vectorSearchScore"
                        }, 
                    } 
            }, 
    ] 

    def sync_search(): 
        return list(_collection.aggregate(pipeline)) 
    
    results = await asyncio.to_thread(sync_search) 
    
    logger.info(f"Vector search returned {len(results)} results") 
    
    return results