import json
import re
from google import genai
from app.api.config import GEMINI_API_KEY, GEMINI_MODEL
from app.utils.logger import setup_logger
logger = setup_logger()

client = genai.Client(api_key=GEMINI_API_KEY)


def extract_json(text: str) -> str:
    """
    Extract the first JSON object from the text using brace counting.
    This ignores any leading/trailing non-JSON text.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object start found in model response")

    brace_count = 0
    in_json = False

    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            brace_count += 1
            in_json = True
        elif ch == "}":
            brace_count -= 1

        if in_json and brace_count == 0:
            return text[start : i + 1]

    raise ValueError("JSON braces never balanced in model response")


def clean_json(json_str: str) -> str:
    """
    Minimal cleanup:
    - remove trailing commas before } or ]
    - remove ellipses
    - strip weird zero-width spaces
    """
    # remove trailing commas like "...,\n}" or "..., ]"
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    # remove "..."
    json_str = json_str.replace("...", "")

    # strip zero-width spaces
    json_str = json_str.replace("\u200b", "")

    return json_str


def parse_or_repair_json(text: str) -> dict:
    """
    Try to parse JSON normally with minimal cleanup.
    For now, we DO NOT attempt continuation.
    If parsing fails, we log and raise so we can see the raw text.
    """

    raw = extract_json(text)
    cleaned = clean_json(raw)

    logger.info("EXTRACTED_JSON_START")
    logger.info(cleaned)
    logger.info("EXTRACTED_JSON_END")

    try:
        parsed = json.loads(cleaned)
        return parsed
    except Exception as e:
        logger.error(f"JSON parse failed even after cleaning: {e}")
        logger.error("RAW_TEXT_START")
        logger.error(text)
        logger.error("RAW_TEXT_END")
        raise