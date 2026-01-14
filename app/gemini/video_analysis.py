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

async def extract_text_from_video(client, video_path: str) -> dict:
    """
    Extracts resume and job description text from a video file.
    It uses Gemini Vision with an OCR fallback and caches the result in Redis.
    """
    video_hash = compute_video_hash(video_path)
    if client.redis:
        cached_text = await client.redis.get(f"video_extract:{video_hash}")
        if cached_text:
            logger.info(f"Video text cache HIT for hash {video_hash}")
            return safe_json_parse(cached_text)
    
    logger.info(f"Video text cache MISS for hash {video_hash}. Processing video.")

    raw_frames = extract_raw_frames(video_path)
    unique_frames = dedupe_frames(raw_frames)
    prepared_frames = prepare_frames(unique_frames)

    prompt = await client.prompts.get("analyze_video")
    content = [prompt] + prepared_frames

    try:
        resp = await client.call(
            "video_text_extraction",
            client.client.models.generate_content,
            model=client.vision_model,
            contents=content,
            generation_config={"response_mime_type": "application/json"},
            safety_settings=client.safety(),
        )
        extracted_text = validate_extraction(safe_json_parse(resp.text))

    except (Exception, GeminiSafetyError) as e:
        logger.warning(f"Gemini Vision failed or was blocked: {e}. Falling back to OCR.")
        extracted_text = ocr_fallback(prepared_frames)

    if client.redis:
        # Use a different key for extracted text to not conflict with final analysis
        await client.redis.set(f"video_extract:{video_hash}", json.dumps(extracted_text), ex=3600)

    return extracted_text