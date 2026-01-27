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

async def stream_resume_analysis(self, resume: str, jd: str):
    prompt_template = await self.prompts.get("analyze_resume")
    prompt = prompt_template.format(resume=resume, jd=jd)
    
    try:
        async_stream = await self.client.models.generate_content_stream(
            model=self.chat_model,
            contents=prompt,
        )
        async for chunk in async_stream:
            yield chunk.text or ""
    except Exception as e:
        logger.error(f"Error streaming resume analysis: {e}")
        yield f"[ERROR] {str(e)}"

async def stream_evaluation(self, question: str, answer: str, resume: str, jd: str):
    prompt_template = await self.prompts.get("evaluate_answer")
    logger.info(f"Prompt template:\n{prompt_template}")
    prompt = prompt_template.format(
        question=question,
        answer=answer,
        resume=resume,
        jd=jd,
    )
    logger.info(f"Formatted prompt:\n{prompt}")
    try:
        async_stream = self.client.models.generate_content_stream(
            model=self.chat_model,
            contents=prompt,
        )
        async for chunk in async_stream:
            text = chunk.text or "" 
            logger.info(f"Streamed chunk: {text}") 
            yield text
    except Exception as e:
        logger.error(f"Error streaming evaluation: {e}")
        yield f"[ERROR] {str(e)}"
