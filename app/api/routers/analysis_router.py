"""
Analysis Router Module

Handles resume + job description analysis, video analysis, and answer evaluation.
Follows Single Responsibility Principle - focuses only on analysis operations.
"""

import tempfile
import os
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse

from app.utils.logger import setup_logger
from app.utils.time_tracker import TimeTracker
from app.api.auth import get_current_user
from app.api.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    EvaluateAnswerRequest,
    EvaluateAnswerResponse,
)
from app.api.app_config import get_config

logger = setup_logger()
config = get_config()
tracker = TimeTracker()

# Will be injected by the main app
agent = None
gemini_client = None
rate_limiter_service = None
quota_service = None

router = APIRouter(prefix="", tags=["Analysis"])


def init_analysis_services(career_agent, gemini_client_instance, rate_limiter, quota):
    """Initialize services - called from main app"""
    global agent, gemini_client, rate_limiter_service, quota_service
    agent = career_agent
    gemini_client = gemini_client_instance
    rate_limiter_service = rate_limiter
    quota_service = quota


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest, current_user: dict = Depends(get_current_user)):
    """
    Analyze resume against job description.
    
    Performs AI-powered analysis to evaluate fit, identify gaps, and provide recommendations.
    
    **Rate Limiting:** 10 requests per minute per user
    **Quota:**
    - Free tier: 5 analyses per day
    - Premium tier: 100 analyses per day
    
    **Returns:** FitGraph visualization + insights
    """
    username = current_user["username"]
    logger.info(f"Received text analysis request from user '{username}'")

    # --- Rate Limiting Check ---
    allowed, rate_info = await rate_limiter_service.is_allowed(username)
    if not allowed:
        logger.warning(f"Rate limit exceeded for user {username}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. {rate_info['remaining']} requests remaining. Resets at {rate_info['reset_at']}",
        )

    # --- Quota Check ---
    can_analyze, quota_info = await quota_service.can_perform_analysis(username)
    if not can_analyze:
        logger.warning(f"Quota exceeded for user {username}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Daily quota exceeded. You have {quota_info['usage']}/{quota_info['limit']} analyses. "
                   f"Upgrade to premium or wait until {quota_info['reset_at']}",
        )

    # Increment usage
    await quota_service.increment_usage(username)

    tracker.mark("text_api_request_received")
    inputs = {
        "resume_text": request.resume_text,
        "jd_text": request.jd_text,
    }
    tracker.mark("text_inputs_prepared")
    
    try:
        final_state = await agent.workflow.ainvoke(inputs)
        logger.info("Graph workflow completed for text analysis.")
        result = final_state.get("final_result")
        
        if not result:
            raise HTTPException(status_code=500, detail="Agent workflow failed to produce a result.")
        
        logger.info("Analysis metrics: %s", result.get("performance_metrics", {}))
        return AnalysisResponse(**final_state.get("final_result", {}))
        
    except Exception as e:
        logger.error(f"Analysis failed during agent execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze_video", response_model=AnalysisResponse)
async def analyze_video(
    current_user: dict = Depends(get_current_user),
    video_file: UploadFile = File(...)
):
    """
    Analyze video interview against job description.
    
    Extracts resume content from video and performs full analysis.
    
    **Rate Limiting:** 10 requests per minute per user
    **Quota:**
    - Free tier: 5 analyses per day
    - Premium tier: 100 analyses per day
    """
    username = current_user["username"]
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

        # Run the workflow
        final_state = await agent.workflow.ainvoke(inputs)
        logger.info("Graph workflow completed for video analysis.")
        
        # Validate workflow output
        if not isinstance(final_state, dict):
            raise HTTPException(500, "Workflow returned invalid state")

        result = final_state.get("final_result")
        if not isinstance(result, dict):
            raise HTTPException(500, "Workflow failed to produce final_result")

        return AnalysisResponse(**final_state.get("final_result", {}))

    finally:
        # Cleanup temp file
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Cleaned up temporary video file: {video_path}")


@router.post("/evaluate_answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer_api(
    payload: EvaluateAnswerRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluate interview answer against resume and job description.
    
    Provides feedback on answer quality and relevance.
    """
    from app.gemini import evaluate_answer
    
    tracker.mark("evaluate_answer_request_received")
    username = current_user["username"]
    logger.info(f"Answer evaluation requested by user '{username}'")
    
    return await evaluate_answer(
        gemini_client,
        payload.question,
        payload.user_answer,
        payload.resume_text,
        payload.jd_text
    )


@router.post("/stream/analyze")
async def stream_analyze(request: AnalysisRequest, current_user: dict = Depends(get_current_user)):
    """
    Stream resume analysis results.
    
    Returns streamed JSON objects as analysis progresses.
    """
    from app.gemini import stream_resume_analysis
    
    username = current_user["username"]
    logger.info(f"Stream analysis requested by user '{username}'")
    
    return StreamingResponse(
        stream_resume_analysis(
            gemini_client,
            request.resume_text,
            request.jd_text,
        ),
        media_type="text/plain"
    )


@router.post("/stream/evaluate")
async def stream_evaluate(payload: EvaluateAnswerRequest, current_user: dict = Depends(get_current_user)):
    """
    Stream answer evaluation results.
    
    Returns streamed feedback as evaluation progresses.
    """
    from app.gemini import stream_evaluation
    
    username = current_user["username"]
    logger.info(f"Stream evaluation requested by user '{username}'")
    
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
