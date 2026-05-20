import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import perplexity
import pprint

pp = pprint.PrettyPrinter(indent=4)

perplexity.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for non-standard schema keys


def require_min_presence(items, key, min_perc=0.1):
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


answer_schema = {
    "query": {"type": "string", "required": True, "minlength": 1},
    "answer_markdown": {"type": "string", "required": True, "minlength": 1},
    "cited_domains": {"type": "list", "required": True, "schema": {"type": "string"}},
    "source_count": {"type": "integer", "required": True, "min": 0},
    "follow_ups": {"type": "list", "required": True, "schema": {"type": "string"}},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_answer():
    result = await perplexity.scrape_answer("What is the best web scraping API in 2026?")
    validator = Validator(answer_schema, allow_unknown=True)
    validate_or_fail(result, validator)
    assert len(result["answer_markdown"]) > 50
    assert len(result["cited_domains"]) > 0
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / "results/answer.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False)
        )
