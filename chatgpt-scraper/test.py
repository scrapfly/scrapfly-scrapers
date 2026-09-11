import pytest
import chatgpt

chatgpt.BASE_CONFIG["cache"] = False


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_conversation():
    result = await chatgpt.scrape_conversation("What is the capital of France?")
    assert isinstance(result, str)
    assert len(result.strip()) > 0
