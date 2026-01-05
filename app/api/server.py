from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

from app.rag.mongo_vector import search, upsert
from .schemas import AnalysisRequest, AnalysisResponse, EvaluateAnswerRequest, EvaluateAnswerResponse, IngestRequest
from app.utils.logger import setup_logger
from app.utils.mongo_handler import mongo_handler
import json

logger = setup_logger()

from redis import asyncio as aioredis
redis_client = aioredis.Redis(
    host="redis", port=6379, 
    decode_responses=True)

from app.gemini.service import GeminiService 
gemini = GeminiService(redis_client=redis_client, logger=logger,
                       embedding_ttl_seconds=60 * 60 * 24 * 30)

from .config import API_TITLE, API_VERSION

app = FastAPI(title=API_TITLE, version=API_VERSION)

@app.on_event("startup")
def startup_event():
    mongo_handler.connect()

@app.on_event("shutdown")
def shutdown_event():
    mongo_handler.close()

# Add middleware for logging and session management
@app.middleware("http")
async def db_handler_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Create a session for the request
    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "start_time": start_time,
        "request_path": request.url.path,
        "request_method": request.method,
    }
    await mongo_handler.insert_session(session_data)
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log the request and response
    log_data = {
        "session_id": session_id,
        "request_path": request.url.path,
        "request_method": request.method,
        "process_time": process_time,
        "status_code": response.status_code,
    }
    await mongo_handler.insert_log(log_data)
    
    return response

# For now, allow all origins so Streamlit UI can call it easily.
# You can tighten this later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    logger.info(
        f"Received analysis request with resume and jd - "
        f"resume_preview={str(request.resume_text)[:100]}, "
        f"jd_preview={str(request.jd_text)[:100]}"
    )

    # Redis Caching
    cache_key = f"analysis:{hash(request.resume_text + request.jd_text)}"
    cached_result = await redis_client.get(cache_key)
    if cached_result:
        logger.info("Cache hit for analysis request.")
        return json.loads(cached_result)

    logger.info("Cache miss for analysis request.")
    try:
        raw = await gemini.analyze_resume_and_jd(request.resume_text, request.jd_text)
        await redis_client.set(cache_key, json.dumps(raw), ex=3600) # Cache for 1 hour
        logger.info(f"Analysis complete and the response is ready to be sent back to the client.")
        return raw
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/evaluate_answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer_api(payload: EvaluateAnswerRequest):
    result = await gemini.evaluate_answer( payload.question, payload.user_answer, payload.resume_text, payload.jd_text )
    return result

@app.post("/rag/search")
async def rag_search(query: str):
    embedding = await gemini.embed(query)
    results = search(embedding, top_k=5)
    return {"results": results}

@app.post("/rag/ingest")
async def rag_ingest(payload: IngestRequest):
    """
    Endpoint to ingest a document into the vector store.
    """
    try:
        embedding = await gemini.embed(payload.text)
        document = {
            "text": payload.text,
            "embedding": embedding,
            "source": payload.source
        }
        result = await upsert(document)
        return {"status": "success", "inserted_id": str(result.upserted_id)}
    except Exception as e:
        logger.error(f"RAG ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse

@app.post("/stream/analyze")
async def stream_analyze(request: AnalysisRequest):
    return StreamingResponse(
        gemini.stream_resume_analysis(
            request.resume_text,
            request.jd_text,
        ),
        media_type="text/plain"
    )

@app.post("/stream/evaluate")
async def stream_evaluate(payload: EvaluateAnswerRequest):
    return StreamingResponse(
        gemini.stream_evaluation(
            payload.question,
            payload.user_answer,
            payload.resume_text,
            payload.jd_text,
        ),
        media_type="text/plain"
    )

