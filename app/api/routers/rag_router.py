"""
RAG (Retrieval Augmented Generation) Router Module

Handles vector search and document ingestion for RAG operations.
Follows Single Responsibility Principle - focuses only on RAG operations.
"""

from fastapi import APIRouter, HTTPException, Depends, status

from app.utils.logger import setup_logger
from app.api.auth import get_current_user, require_role
from app.api.schemas import IngestRequest
from app.rag.mongo_vector import search, upsert

logger = setup_logger()

# Will be injected by the main app
gemini_client = None

router = APIRouter(prefix="/rag", tags=["RAG"])


def init_rag_services(gemini_client_instance):
    """Initialize services - called from main app"""
    global gemini_client
    gemini_client = gemini_client_instance


@router.post("/search")
async def rag_search(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Search vector database for relevant documents.
    
    Uses semantic search to find documents matching the query.
    
    **Parameters:**
    - query: Search query string
    
    **Returns:** List of matching documents (top 5)
    """
    username = current_user["username"]
    logger.info(f"RAG search requested by user '{username}': {query}")
    
    try:
        from app.gemini import embed
        
        embedding_vector = await embed(gemini_client, query)
        results = search(embedding_vector, top_k=5)
        
        logger.info(f"RAG search completed: found {len(results)} results")
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def rag_ingest(
    payload: IngestRequest,
    current_user: dict = Depends(require_role("admin"))
):
    """
    Ingest and index new documents for RAG.
    
    Creates embeddings and stores in vector database.
    
    **Access:** Admin only
    
    **Parameters:**
    - text: Document content
    - source: Source identifier (filename, URL, etc.)
    
    **Returns:** Document ID and ingestion status
    """
    username = current_user["username"]
    logger.info(f"RAG ingest requested by admin '{username}'")
    
    try:
        from app.gemini import embed
        
        embedding_vector = await embed(gemini_client, payload.text)

        document = {
            "text": payload.text,
            "embedding": embedding_vector,
            "source": payload.source
        }

        result = await upsert(document)
        logger.info(f"Document ingested successfully: {result.upserted_id}")
        
        return {
            "status": "success",
            "inserted_id": str(result.upserted_id),
            "source": payload.source
        }

    except Exception as e:
        logger.error(f"RAG ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
