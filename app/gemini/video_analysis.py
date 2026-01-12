from .video_extraction import (
    compute_video_hash,
    extract_raw_frames,
    dedupe_frames,
    prepare_frames,
    ocr_fallback,
    validate_extraction,
)
from .json_utils import safe_json_parse


async def analyze_video_and_jd(client, video_path):
    video_hash = compute_video_hash(video_path)

    if client.redis:
        cached = await client.redis.get(f"video_extract:{video_hash}")
        if cached:
            data = safe_json_parse(cached)
            return await client.text_analysis.analyze_resume_and_jd(
                data["resume_text"], data["jd_text"]
            )

    raw = extract_raw_frames(video_path)
    unique = dedupe_frames(raw)
    prepared = prepare_frames(unique)

    prompt = await client.prompts.get("analyze_video")
    content = [prompt] + prepared

    resp = await client.call(
        "video_text_extraction",
        client.client.models.generate_content,
        model=client.vision_model,
        contents=content,
        generation_config={"response_mime_type": "application/json"},
        safety_settings=client.safety(),
    )

    extracted = validate_extraction(safe_json_parse(resp.text)) or ocr_fallback(prepared)

    if client.redis:
        await client.redis.set(f"video_extract:{video_hash}", extracted)

    return await client.text_analysis.analyze_resume_and_jd(
        extracted["resume_text"], extracted["jd_text"]
    )
