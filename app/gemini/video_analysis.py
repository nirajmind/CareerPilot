import json
import base64
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

    prompt_text = await client.prompts.get("analyze_video")
    
    parts = [{"text": prompt_text}]
    
    for frame in prepared_frames:
        # data is bytes, need to base64 encode for JSON payload
        b64_data = base64.b64encode(frame["data"]).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": frame["mime_type"],
                "data": b64_data
            }
        })
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"response_mime_type": "application/json"},
        # Safety settings - assuming defaults or simple mapping if needed, 
        # but for now we'll rely on server-side defaults or if client.safety() returns compatible dict list, 
        # checking client.safety() structure from previous context it was a dict of objects, not compatible with JSON list.
        # We will omit safety_settings for now as the proxy/endpoint defaults might suffice, or we'd need to convert keys to strings.
        # Given the instruction to just fix the call, I will omit explicit safety settings here unless critical.
    }

    logger.debug(f"Gemini Vision content prepared with {len(prepared_frames)} frames")

    try:
        tracker.mark("gemini_vision_call_start")
        
        resp = await client.call(
            "video_text_extraction",
            f"{client.vision_model}:generateContent",
            payload
        )
        
        tracker.mark("gemini_vision_call_end")
        
        # resp is a dict (JSON response)
        # Structure: candidates[0].content.parts[0].text
        logger.debug(f"Gemini Vision raw response keys: {list(resp.keys())}")
        
        try:
            text_content = resp["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            logger.error(f"Unexpected response structure: {resp}")
            raise ValueError("Invalid response structure from Gemini")

        parsed_response = safe_json_parse(text_content)
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