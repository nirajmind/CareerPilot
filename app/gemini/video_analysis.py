import json
from .video_extraction import (
    compute_video_hash,
    extract_raw_frames,
    dedupe_frames,
    prepare_frames,
    ocr_fallback,
    validate_extraction,
)
from .json_utils import safe_json_parse
from .logger import logger
from .exceptions import GeminiSafetyError
from app.utils.time_tracker import TimeTracker

tracker = TimeTracker()

async def extract_text_from_video(client, video_path: str) -> dict:
    """
    Extracts resume and job description text from a video file.
    It uses Gemini Vision with an OCR fallback and caches the result in Redis.
    """
    tracker.mark("video_analysis_started")
    video_hash = compute_video_hash(video_path)
    if client.redis:
        cached_text = await client.redis.get(f"video_extract:{video_hash}")
        if cached_text:
            logger.info(f"Video text cache HIT for hash {video_hash}")
            tracker.mark("video_analysis_cache_hit")
            return safe_json_parse(cached_text)
    
    logger.info(f"Video text cache MISS for hash {video_hash}. Processing video.")
    tracker.mark("video_analysis_cache_miss")
    raw_frames = extract_raw_frames(video_path)
    tracker.mark("raw_frames_extracted")
    unique_frames = dedupe_frames(raw_frames)
    tracker.mark("frames_deduplicated")
    prepared_frames = prepare_frames(unique_frames)
    tracker.mark("frames_prepared_for_api")
    prompt = await client.prompts.get("analyze_video")
    content = [prompt] + prepared_frames
    logger.debug(f"Gemini Vision content: {content}")

    try:
        tracker.mark("gemini_vision_call_start")
        resp = await client.call(
            "video_text_extraction",
            client.client.models.generate_content,
            model=client.vision_model,
            contents=content,
            generation_config={"response_mime_type": "application/json"},
            safety_settings=client.safety(),
        )
        tracker.mark("gemini_vision_call_end")
        logger.debug(f"Gemini Vision raw response: {resp.text}")
        parsed_response = safe_json_parse(resp.text)
        logger.debug(f"Gemini Vision parsed response: {parsed_response}")
        extracted_text = validate_extraction(parsed_response)
        logger.info(f"Gemini Vision validation successful.")
        tracker.mark("gemini_vision_validation_complete")

    except (Exception, GeminiSafetyError) as e:
        logger.warning(f"Gemini Vision failed or was blocked: {e}. Falling back to OCR.")
        tracker.mark("gemini_vision_failed_starting_ocr")
        extracted_text = ocr_fallback(prepared_frames)
        tracker.mark("ocr_fallback_complete")
        logger.debug(f"OCR fallback result: {extracted_text}")

    if client.redis:
        # Use a different key for extracted text to not conflict with final analysis
        await client.redis.set(f"video_extract:{video_hash}", json.dumps(extracted_text), ex=3600)
        tracker.mark("video_text_cached")
        
    tracker.mark("video_analysis_finished")    
    logger.info(f"Returning extracted text from video: {extracted_text}")
    return extracted_text