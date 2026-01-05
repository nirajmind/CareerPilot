from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.rag.mongo_vector import search

from .schemas import AnalysisRequest, AnalysisResponse, EvaluateAnswerRequest, EvaluateAnswerResponse

from app.utils.logger import setup_logger
logger = setup_logger()

import redis
redis_client = redis.Redis(
    host="redis", port=6379, 
    decode_responses=True)

from app.gemini.service import GeminiService 
gemini = GeminiService(redis_client=redis_client, logger=logger,
                       embedding_ttl_seconds=60 * 60 * 24 * 30)

from .config import API_TITLE, API_VERSION

app = FastAPI(title=API_TITLE, version=API_VERSION)

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
    logger.info(f"AnalysisRequest JSON: {request.model_dump_json()}")
    logger.info(
        f"Received analysis request with resume and jd - "
        f"resume_preview={str(request.resume_text)[:100]}, "
        f"jd_preview={str(request.jd_text)[:100]}"
        )
    try:
        raw = await gemini.analyze_resume_and_jd(request.resume_text, request.jd_text)
        logger.info(f"Analysis complete and the response is ready to be sent back to the client."
                    f"raw_preview={raw}")
        return raw
    except Exception as e:
        # Later: log this, add better error struct
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

from fastapi.responses import StreamingResponse

@app.post("/stream/analyze")
async def stream_analyze(request: AnalysisRequest):
    async def event_generator():
        async for chunk in gemini.stream_resume_analysis(
            request.resume_text,
            request.jd_text,
        ):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.post("/stream/evaluate")
async def stream_evaluate(payload: EvaluateAnswerRequest):
    async def event_generator():
        async for chunk in gemini.stream_evaluation(
            payload.question,
            payload.user_answer,
            payload.resume_text,
            payload.jd_text,
        ):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/plain")

