from fastapi import FastAPI, HTTPException, Request, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, StreamingResponse

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

# --- LangGraph Agent ---
agent = CareerPilotAgent(gemini_client=gemini_client, redis_client=redis_client)

# --- FastAPI App ---
app = FastAPI(title=API_TITLE, version=API_VERSION)

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
        "username": user.username,
        "hashed_password": hashed_password,
        "roles": user.roles,
        "is_active": True,
    })

    return {"message": "User created successfully"}


@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await mongo_handler.get_user(form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):
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
        data={"sub": user["username"], "roles": user["roles"]}
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
    
    inputs = {
        "resume_text": request.resume_text,
        "jd_text": request.jd_text,
    }
    
    try:
        final_state = None
        async for state_update in agent.workflow.astream(inputs):
            if "__end__" in state_update:
                final_state = state_update.get('__end__', {})

        result = final_state.get("final_result")
        if not result:
            raise HTTPException(status_code=500, detail="Agent workflow failed to produce a result.")
        return result
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
    if not video_file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")

    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(await video_file.read())
        video_path = tmp.name

    logger.info(f"Video saved to temporary file: {video_path}")

    try:
        # Prepare workflow input
        inputs = {"video_file_path": video_path}

        # Run the workflow (langgraph 0.2.3)
        final_state = await agent.workflow.ainvoke(inputs)

        # Validate workflow output
        if not isinstance(final_state, dict):
            raise HTTPException(500, "Workflow returned invalid state")

        raw_result = final_state["final_result"] 
        
        # 3. Ensure we have a dict from JSON 
        if isinstance(raw_result, str): 
            try: 
                payload = json.loads(raw_result) 
            except json.JSONDecodeError as e: 
                logger.error(f"Failed to parse LLM JSON: {e} | raw={raw_result!r}") 
                raise HTTPException(status_code=500, detail="LLM returned invalid JSON") 
        elif isinstance(raw_result, dict): 
            # Already a dict, but may have come from Python repr; still usable as a mapping 
            payload = raw_result 

        else: 
            logger.error(f"Unexpected final_result type: {type(raw_result)}") 
            raise HTTPException(status_code=500, detail="Unexpected agent result format") 
        # 4. Normalize keys from LLM structure -> AnalysisResponse schema 
        fit_graph_src = payload.get("FitGraph", {}) or {} 
        resume_src = payload.get("ResumeAnalysis", {}) or {} 
        feedback_src = payload.get("ActionableFeedback", {}) or {} 
        interview_src = payload.get("InterviewPrep", {}) or {} 
        # ---- FitGraph mapping ---- 
        fitgraph = { 
            "match_score": fit_graph_src.get("overall_match_percentage", 0), 
            "matching_skills": [ 
                s for s in fit_graph_src.get("skills_breakdown", []) 
                if s.get("match_level") not in (None, "None") 
                ],
            "missing_skills": [ 
                s for s in fit_graph_src.get("skills_breakdown", []) 
                if s.get("match_level") == "None" 
                ], 
                # You can derive these however you like; here we just default 
                "growth_potential": [], 
                "risk_areas": [], 
                } 
        # ---- ResumeAnalysis mapping ---- 
        resume_analysis = { 
            # If you want a summary, you can synthesize one later; keep it non-null 
            "summary": "", 
            "strengths": resume_src.get("strengths", []) or [], 
            "gaps": resume_src.get("weaknesses", []) or [], 
            "recommendations": feedback_src.get("resume_optimization", []) or [], 
            } 
        # ---- JD Analysis mapping ---- 
        jd_analysis = { 
            "summary": "", 
            "must_haves": resume_src.get("keywords_missing", []) or [], 
            "nice_to_haves": [], 
            # you can derive from context later 
            "hidden_signals": [], 
            } 
        # ---- Skill Matrix mapping ---- 
        skill_matrix = { 
            "strengths": resume_src.get("keywords_found", []) or [], 
            "gaps": resume_src.get("keywords_missing", []) or [], 
            "emerging": [], 
            } 
        # ---- Preparation Plan mapping ---- 
        priority = {
            "high": feedback_src.get("critical_improvements", []),
            "medium": feedback_src.get("resume_optimization", []),
            "low": []
            }
        preparation_plan = {
            "steps": feedback_src.get("critical_improvements", []),
            "priority": priority
            }

        # ---- Mock Interview mapping ---- 
        mock_interview = { 
            "questions": interview_src.get("technical_questions", []) or [], 
            "follow_ups": [], 
            "behavioral": [], 
            } 
        # ---- Resume rewrite & next steps (keep non-null) ---- 
        resume_rewrite = "" 
        # you can ask the LLM for this later 
        next_steps = feedback_src.get("critical_improvements", []) or [] 
        # 5. Build the Pydantic response model 
        response = AnalysisResponse( 
            fitgraph=fitgraph, 
            resume_analysis=resume_analysis, 
            jd_analysis=jd_analysis, 
            skill_matrix=skill_matrix, 
            preparation_plan=preparation_plan, 
            mock_interview=mock_interview, 
            resume_rewrite=resume_rewrite, 
            next_steps=next_steps, 
            ) 
        
        return response 
    
    finally: 
        if video_path and os.path.exists(video_path): 
            os.remove(video_path)

# ---------------------------------------------------------
# Evaluate Answer
# ---------------------------------------------------------
@app.post("/evaluate_answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer_api(
    payload: EvaluateAnswerRequest,
    current_user: dict = Depends(get_current_user)
):
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
