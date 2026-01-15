import json
import re
from .logger import logger


def safe_json_parse(text: str):
    """
    Fully instrumented JSON parser for LLM output.
    Logs every step so you can see exactly what is happening.
    """

    original_text = text
    logger.debug("[JSON] === RAW INPUT START ===")
    logger.debug(text)
    logger.debug("[JSON] === RAW INPUT END ===")

    # ---------------------------------------------------------
    # 1. Remove docker timestamps
    # ---------------------------------------------------------
    text_no_ts = re.sub(
        r"^\s*\d{4}-\d{2}-\d{2}.*?\|\s*",
        "",
        text,
        flags=re.MULTILINE
    )
    logger.debug("[JSON] After removing timestamps:")
    logger.debug(text_no_ts)

    # ---------------------------------------------------------
    # 2. Remove markdown fences
    # ---------------------------------------------------------
    cleaned = re.sub(r"```json", "", text_no_ts, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned)
    cleaned = cleaned.strip()

    logger.debug("[JSON] After removing fences:")
    logger.debug(cleaned)

    # ---------------------------------------------------------
    # 3. STRICT PARSE
    # ---------------------------------------------------------
    try:
        parsed = json.loads(cleaned)
        logger.info("[JSON] Strict parse succeeded")
        return parsed
    except Exception as e:
        logger.debug(f"[JSON] Strict parse failed: {e}")

    # ---------------------------------------------------------
    # 4. BALANCED JSON EXTRACTION
    # ---------------------------------------------------------
    logger.debug("[JSON] Attempting balanced JSON extraction")
    candidate = extract_balanced_json(cleaned)

    if candidate:
        logger.debug("[JSON] Balanced candidate extracted:")
        logger.debug(candidate)

        try:
            parsed = json.loads(candidate)
            logger.info("[JSON] Balanced parse succeeded")
            return parsed
        except Exception as e:
            logger.debug(f"[JSON] Balanced parse failed: {e}")
    else:
        logger.debug("[JSON] Balanced extraction returned None")

    # ---------------------------------------------------------
    # 5. REPAIR STEP
    # ---------------------------------------------------------
    repaired = (
        cleaned.replace("\n", " ")
               .replace(",}", "}")
               .replace(",]", "]")
               .strip()
    )

    logger.debug("[JSON] Repaired candidate:")
    logger.debug(repaired)

    try:
        parsed = json.loads(repaired)
        logger.info("[JSON] Repair parse succeeded")
        return parsed
    except Exception as e:
        logger.debug(f"[JSON] Repair parse failed: {e}")

    # ---------------------------------------------------------
    # 6. FINAL FALLBACK
    # ---------------------------------------------------------
    logger.warning("[JSON] All parsing attempts failed. Returning raw text.")
    return {"raw_text": original_text}



def extract_balanced_json(text: str):
    """
    Extracts the first balanced {...} JSON object.
    Deep debugging added to understand brace behavior.
    """

    logger.debug("[JSON][BALANCED] Starting balanced extraction")

    start = text.find("{")
    logger.debug(f"[JSON][BALANCED] First '{{' at index: {start}")

    if start == -1:
        logger.debug("[JSON][BALANCED] No opening brace found")
        return None

    depth = 0
    for i in range(start, len(text)):
        char = text[i]

        if char == "{":
            depth += 1
            logger.debug(f"[JSON][BALANCED] '{{' at {i}, depth -> {depth}")

        elif char == "}":
            depth -= 1
            logger.debug(f"[JSON][BALANCED] '}}' at {i}, depth -> {depth}")

            if depth == 0:
                candidate = text[start:i+1]
                logger.debug(f"[JSON][BALANCED] Balanced JSON ends at index {i}")
                logger.debug("[JSON][BALANCED] Extracted candidate:")
                logger.debug(candidate)
                return candidate

    logger.debug("[JSON][BALANCED] No balanced JSON found — input may be truncated")
    logger.debug(f"[JSON][BALANCED] Final depth: {depth}")
    logger.debug(f"[JSON][BALANCED] Text length: {len(text)}")
    logger.debug("[JSON][BALANCED] Text snippet:")
    logger.debug(text[:500])

    return None
