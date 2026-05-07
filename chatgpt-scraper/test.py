import os
from cerberus import Validator
import pytest
import chatgpt
import pprint

pp = pprint.PrettyPrinter(indent=4)

chatgpt.BASE_CONFIG["cache"] = False


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


conversation_schema = {
    "conversation_id": {"type": "string"},
    "messages": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "role": {"type": "string"},
                "content": {"type": "string"},
            },
        },
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_conversation():
    result = await chatgpt.scrape_conversation("What is the capital of France?")
    assert isinstance(result, str)
    assert len(result.strip()) > 0



@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_conversations():
    prompts = [
        "What is the best web scraping service in 2026?",
        "summarize the previous answer in 200 words",
    ]
    result = await chatgpt.scrape_conversations(prompts)
    validator = Validator(conversation_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 1



@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_search_queries():
    result = await chatgpt.scrape_search_queries(
        "what is the best web scraping service in 2026? keywords for searching How to scrape IG. most reviewed Capterra"
    )
    assert result is not None
    assert len(result) >= 1
    for query in result:
        assert isinstance(query, str)
        assert len(query.strip()) > 0
