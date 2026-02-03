from .json_utils import safe_json_parse
from .logger import logger



async def analyze_resume_and_jd(client, resume: str, jd: str):
    prompt_template = await client.prompts.get("analyze_resume")
    prompt = prompt_template.replace("{resume}", resume).replace("{jd}", jd)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        resp = await client.call(
            "resume_analysis",
            f"{client.chat_model}:generateContent",
            payload
        )
        # resp is dict
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        return safe_json_parse(text)
    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        # Return empty dict or re-raise? Original code didn't catch explicitly here but caller might.
        # Original code just accessed props which would raise if failed.
        # We should probably let it raise or handle safely.
        raise e


async def evaluate_answer(client, question, answer, resume, jd):
    prompt_template = await client.prompts.get("evaluate_answer")

    prompt = prompt_template.format(
        question=question,
        answer=answer,
        resume=resume,
        jd=jd,
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    resp = await client.call(
        "evaluate_answer",
        f"{client.chat_model}:generateContent",
        payload
    )

    text = resp["candidates"][0]["content"]["parts"][0]["text"]
    return safe_json_parse(text)

async def stream_resume_analysis(client, resume: str, jd: str):
    prompt_template = await client.prompts.get("analyze_resume")
    prompt = prompt_template.format(resume=resume, jd=jd)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        # Use our proxy-aware streaming method
        async for chunk_obj in client.call_stream(
            "stream_resume_analysis",
            f"{client.chat_model}:generateContent",
            payload
        ):
            # chunk_obj is the raw JSON response
            # Navigate to candidates[0].content.parts[0].text
            try:
                text_chunk = chunk_obj["candidates"][0]["content"]["parts"][0]["text"]
                if text_chunk:
                    yield text_chunk
            except (KeyError, IndexError):
                # Some chunks might be metadata or empty
                continue
                
    except Exception as e:
        logger.error(f"Error streaming resume analysis: {e}")
        yield f"[ERROR] {str(e)}"

async def stream_evaluation(client, question: str, answer: str, resume: str, jd: str):
    prompt_template = await client.prompts.get("evaluate_answer")
    logger.info(f"Prompt template length: {len(prompt_template)}")
    
    prompt = prompt_template.format(
        question=question,
        answer=answer,
        resume=resume,
        jd=jd,
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        async for chunk_obj in client.call_stream(
            "stream_evaluation",
            f"{client.chat_model}:generateContent",
            payload
        ):
            try:
                text_chunk = chunk_obj["candidates"][0]["content"]["parts"][0]["text"]
                if text_chunk:
                    logger.debug(f"Streamed chunk: {text_chunk[:20]}...") 
                    yield text_chunk
            except (KeyError, IndexError):
                continue
                
    except Exception as e:
        logger.error(f"Error streaming evaluation: {e}")
        yield f"[ERROR] {str(e)}"
