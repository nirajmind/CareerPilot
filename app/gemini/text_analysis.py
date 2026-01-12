from .json_utils import safe_json_parse
from .logger import logger


async def analyze_resume_and_jd(client, resume: str, jd: str):
    prompt_template = await client.prompts.get("analyze_resume")
    prompt = prompt_template.replace("{resume}", resume).replace("{jd}", jd)

    resp = await client.call(
        "resume_analysis",
        client.client.models.generate_content,
        model=client.chat_model,
        contents=prompt,
    )

    text = resp.candidates[0].content.parts[0].text
    return safe_json_parse(text)


async def evaluate_answer(client, question, answer, resume, jd):
    prompt_template = await client.prompts.get("evaluate_answer")

    prompt = prompt_template.format(
        question=question,
        answer=answer,
        resume=resume,
        jd=jd,
    )

    resp = await client.call(
        "evaluate_answer",
        client.client.models.generate_content,
        model=client.chat_model,
        contents=prompt,
    )

    return safe_json_parse(resp.text)

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
    prompt = prompt_template.format(
        question=question,
        answer=answer,
        resume=resume,
        jd=jd,
    )
    try:
        async_stream = await self.client.models.generate_content_stream(
            model=self.chat_model,
            contents=prompt,
        )
        async for chunk in async_stream:
            yield chunk.text or ""
    except Exception as e:
        logger.error(f"Error streaming evaluation: {e}")
        yield f"[ERROR] {str(e)}"
