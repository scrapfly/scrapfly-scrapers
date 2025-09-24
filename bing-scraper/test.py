import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import bing
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
bing.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


serp_schema = {
    "position": {"type": "integer"},
    "title": {"type": "string"},
    "url": {"type": "string"},
    "origin": {"type": "string"},
    "domain": {"type": "string"},
    "description": {"type": "string"},
    "date": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_serp_scraping():
    serp_data = await bing.scrape_search(query="web scraping emails", max_pages=3)
    validator = Validator(serp_schema, allow_unknown=True)
    for item in serp_data:
        validate_or_fail(item, validator)
    for k in serp_schema:
        require_min_presence(
            serp_data, k, min_perc=serp_schema[k].get("min_presence", 0.1)
        )
    assert len(serp_data) >= 10
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/serps.json').write_text(json.dumps(serp_data, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_keyword_scraping():
    keyword_data = await bing.scrape_keywords(query="web scraping emails")
    assert len(keyword_data) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/keywords.json').write_text(json.dumps(keyword_data, indent=2, ensure_ascii=False))
