import pytest
import os

@pytest.mark.asyncio
async def test_prompt_loader_file(gemini):
    # Ensure prompt file exists
    path = "app/gemini/prompts/analyze_resume.txt"
    assert os.path.exists(path)

    text = await gemini.prompts.get("analyze_resume")
    assert "{resume}" in text
