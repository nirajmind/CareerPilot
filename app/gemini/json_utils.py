import json
import re
from .logger import logger


def safe_json_parse(text):
    """
        Attempts to parse JSON from LLM output safely.
        - Handles markdown fences
        - Extracts JSON substring
        - Repairs common formatting issues
        - Logs failures
    """
    # 1. Direct strict parse
    try:
        return json.loads(text)
    except Exception:
        logger.error(f"[GeminiService] Failed to parse JSON from response - {text}")
        pass

    # 2. Remove markdown fences
    cleaned = re.sub(r"```json\s*|```\s*", "", text, flags=re.MULTILINE).strip()
    logger.info(f"[GeminiService] Parsing JSON from cleaned response - {cleaned}")
    try:
        return json.loads(cleaned)
    except Exception:
        logger.error(f"[GeminiService] Failed to parse JSON from cleaned response - {cleaned}")
        pass

    # 3. Extract JSON substring using regex
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except Exception:
            logger.error(f"[GeminiService] Failed to parse JSON from match response - {json_match.group(0)}")
            pass

    # 4. Attempt common repairs
    repaired = (
        cleaned.replace("\n", " ")
        .replace(",}", "}")
        .replace(",]", "]")
    )
    logger.info(f"[GeminiService] Parsing JSON from repaired response - {repaired}")
    try:
        return json.loads(repaired)
    except Exception as e:
        logger.error(f"[GeminiService] Failed to parse JSON: {e}")
        logger.error(f"[GeminiService] Failed to parse JSON from response - {repaired}")
        pass

    # 5. Final fallback: return raw text
    if logger:
        logger.warning(f"[GeminiService] Failed to parse JSON. Returning raw text.")

    logger.info(f"[GeminiService] Parsed json from response - {text}")
    return {"raw_text": text}
