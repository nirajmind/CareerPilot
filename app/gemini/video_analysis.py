from asyncio.log import logger

from app.gemini.exceptions import GeminiSafetyError
from .video_extraction import (
    compute_video_hash,
    extract_raw_frames,
    dedupe_frames,
    prepare_frames,
    ocr_fallback,
    validate_extraction,
)
from .json_utils import safe_json_parse
from .text_analysis import analyze_resume_and_jd

async def analyze_video_and_jd(client, video_path):
    video_hash = compute_video_hash(video_path)

    if client.redis:
        cached = await client.redis.get(f"video_extract:{video_hash}")
        if cached:
            data = safe_json_parse(cached)
            return await analyze_resume_and_jd(
                data["resume_text"], data["jd_text"]
            )

    logger.info("[Video] Extracting raw frames")
    raw = extract_raw_frames(video_path)
    logger.info(f"[Video] Raw frames count: {len(raw)}")
    logger.info("[Video] Deduplicating frames")
    unique = dedupe_frames(raw)
    logger.info(f"[Video] Unique frames count: {len(unique)}") 
    logger.info("[Video] Preparing frames for Gemini")
    prepared = prepare_frames(unique)
    logger.info(f"[Video] Prepared frames count: {len(prepared)}")
    prompt = await client.prompts.get("analyze_video")
    content = [prompt] + prepared
    logger.debug(
    "[Gemini] Vision input summary",
    extra={
        "frame_count": len(prepared),
        "prompt_length": len(prompt),
        "model": client.vision_model,
        }
    )

    try: 
        resp = await client.call( 
            "video_text_extraction", 
            client.client.models.generate_content, 
            model=client.vision_model, 
            contents=content, 
            generation_config={"response_mime_type": "application/json"}, 
            safety_settings=client.safety(),
            ) 
    except Exception as e: 
        # Gemini Vision blocked BEFORE generating JSON 
        logger.warning(f"[Gemini] Vision blocked early: {e}") 
        extracted = ocr_fallback(prepared) 
        return await analyze_resume_and_jd(
             client, extracted["resume_text"], extracted["jd_text"] 
            )

    if hasattr(resp, "prompt_feedback"): 
        logger.warning( "[Gemini] Prompt feedback", extra={"feedback": resp.prompt_feedback} ) 
        
    if hasattr(resp, "candidates"): 
        for c in resp.candidates: 
            if hasattr(c, "safety_ratings"): 
                logger.warning( "[Gemini] Safety ratings", extra={"ratings": c.safety_ratings} )

    try:
        extracted = validate_extraction(safe_json_parse(resp.text))
    except GeminiSafetyError:
        logger.warning("Vision blocked — falling back to OCR")
        extracted = ocr_fallback(prepared)

    if client.redis:
        await client.redis.set(f"video_extract:{video_hash}", extracted)

    return await analyze_resume_and_jd(client, extracted["resume_text"], extracted["jd_text"])