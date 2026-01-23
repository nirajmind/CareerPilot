from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, StreamingResponse
from app.utils.time_tracker import TimeTracker
import json
import time
import uuid
import tempfile
import os

from redis import asyncio as aioredis
from requests import request

from app.utils.logger import setup_logger
from app.utils.mongo_handler import mongo_handler
from app.api.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_role
)
from app.rag.mongo_vector import search, upsert
from .schemas import (
    AnalysisRequest, AnalysisResponse, EvaluateAnswerRequest,
    EvaluateAnswerResponse, IngestRequest, UserCreate, Token, User
)
from app.api.mock_interview import router as mock_router
from app.api.analysis_history import router as analysis_history_router

# --- Gemini Modular Imports ---
from app.gemini import (
    GeminiClient,
    evaluate_answer,
    stream_resume_analysis,
    stream_evaluation,
    embed,
    extract_text_from_video
)

# --- Agent Imports ---
from app.agent.workflow import CareerPilotAgent

from .config import API_TITLE, API_VERSION

logger = setup_logger()

# --- Redis Client ---
redis_client = aioredis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)

# --- Gemini Client ---
gemini_client = GeminiClient(redis_client=redis_client)
tracker = TimeTracker()
# --- LangGraph Agent ---
agent = CareerPilotAgent(gemini_client=gemini_client, redis_client=redis_client)

# --- FastAPI App ---
app = FastAPI(title=API_TITLE, version=API_VERSION)
app.include_router(mock_router)
app.include_router(analysis_history_router)

@app.exception_handler(Exception) 
async def global_exception_handler(request: Request, exc: Exception): 
    logger.exception("Unhandled exception occurred") 
    return JSONResponse( status_code=500, content={"error": str(exc)} )

# ---------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------
@app.on_event("startup")
def startup_event():
    mongo_handler.connect()

@app.on_event("shutdown")
def shutdown_event():
    mongo_handler.close()


# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------
@app.middleware("http")
async def db_handler_middleware(request: Request, call_next):
    start_time = time.time()
    session_id = str(uuid.uuid4())

    await mongo_handler.insert_session({
        "session_id": session_id,
        "start_time": start_time,
        "request_path": request.url.path,
        "request_method": request.method,
    })

    response = await call_next(request)

    await mongo_handler.insert_log({
        "session_id": session_id,
        "request_path": request.url.path,
        "request_method": request.method,
        "process_time": time.time() - start_time,
        "status_code": response.status_code,
    })

    return response


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------
@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    existing_user = await mongo_handler.get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user.password)
    await mongo_handler.create_user({
        "email": user.email, 
        "username": user.username, 
        "password_hash": hashed_password,
        "roles": user.roles, 
        "is_active": True, 
        "created_at": datetime.now(), 
        "updated_at": datetime.now(),
    })

    return {"message": "User created successfully"}


@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await mongo_handler.get_user(form_data.username)

    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    token = create_access_token(
        data={"sub": user["username"], "roles": user["roles"], 
              "email": user["email"]}
    )

    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------
# Resume + JD Analysis
# ---------------------------------------------------------
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest, current_user: dict = Depends(get_current_user)):
    logger.info(f"Received text analysis request from user '{current_user['username']}'")
    tracker.mark("text_api_request_received")
    inputs = {
        "resume_text": request.resume_text,
        "jd_text": request.jd_text,
    }
    tracker.mark("text_inputs_prepared")
    try:

        final_state = await agent.workflow.ainvoke(inputs)
        logger.info("Graph workflow completed for text.")
        result = final_state.get("final_result")
        if not result:
            raise HTTPException(status_code=500, detail="Agent workflow failed to produce a result.")
        
        logger.info("Performance Metrics: %s", result["performance_metrics"])
        return AnalysisResponse(**final_state.get("final_result", {}))
    except Exception as e:
        logger.error(f"Analysis failed during agent execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Video Analysis
# ---------------------------------------------------------
@app.post("/analyze_video", response_model=AnalysisResponse)
async def analyze_video(
    current_user: dict = Depends(get_current_user),
    video_file: UploadFile = File(...)
):
    tracker.mark("video_api_request_received")
    if not video_file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")

    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(await video_file.read())
        video_path = tmp.name
    tracker.mark("video_file_saved_to_temp")
    logger.info(f"Video saved to temporary file: {video_path}")

    try:
        # Prepare workflow input
        inputs = {"video_file_path": video_path}

        # Run the workflow (langgraph 0.2.3)
        final_state = await agent.workflow.ainvoke(inputs)
        logger.info("Graph workflow completed for video.")
        # Validate workflow output
        if not isinstance(final_state, dict):
            raise HTTPException(500, "Workflow returned invalid state")

        result = final_state.get("final_result")
        if not isinstance(result, dict):
            raise HTTPException(500, "Workflow failed to produce final_result")

        # Return the final result (FastAPI will validate against AnalysisResponse)
        return AnalysisResponse(**final_state.get("final_result", {}))

    finally:
        # Cleanup temp file
        if os.path.exists(video_path):
            os.remove(video_path)

# ---------------------------------------------------------
# Evaluate Answer
# ---------------------------------------------------------
@app.post("/evaluate_answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer_api(
    payload: EvaluateAnswerRequest,
    current_user: dict = Depends(get_current_user)
):  
    tracker.mark("evaluate_answer_request_received")
    return await evaluate_answer(
        gemini_client,
        payload.question,
        payload.user_answer,
        payload.resume_text,
        payload.jd_text
    )


# ---------------------------------------------------------
# RAG Search
# ---------------------------------------------------------
@app.post("/rag/search")
async def rag_search(query: str, current_user: dict = Depends(get_current_user)):
    embedding_vector = await embed(gemini_client, query)
    results = search(embedding_vector, top_k=5)
    return {"results": results}


# ---------------------------------------------------------
# RAG Ingest
# ---------------------------------------------------------
@app.post("/rag/ingest")
async def rag_ingest(payload: IngestRequest, current_user: dict = Depends(require_role("admin"))):
    try:
        embedding_vector = await embed(gemini_client, payload.text)

        document = {
            "text": payload.text,
            "embedding": embedding_vector,
            "source": payload.source
        }

        result = await upsert(document)
        return {"status": "success", "inserted_id": str(result.upserted_id)}

    except Exception as e:
        logger.error(f"RAG ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Streaming Endpoints
# ---------------------------------------------------------
@app.post("/stream/analyze")
async def stream_analyze(request: AnalysisRequest, current_user: dict = Depends(get_current_user)):
    return StreamingResponse(
        stream_resume_analysis(
            gemini_client,
            request.resume_text,
            request.jd_text,
        ),
        media_type="text/plain"
    )


@app.post("/stream/evaluate")
async def stream_evaluate(payload: EvaluateAnswerRequest, current_user: dict = Depends(get_current_user)):
    return StreamingResponse(
        stream_evaluation(
            gemini_client,
            payload.question,
            payload.user_answer,
            payload.resume_text,
            payload.jd_text,
        ),
        media_type="text/plain"
    )
