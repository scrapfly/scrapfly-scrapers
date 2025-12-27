"""Test the naver scraper"""

import os
from cerberus import Validator as _Validator
import naver
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
naver.BASE_CONFIG["cache"] = True


# Custom Validator to support min_presence
class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


# Schema definitions
SEARCH_WEB_SCHEMA = {
    "title": {"type": "string", "required": True, "min_presence": 0.9},
    "url": {"type": "string", "required": True, "min_presence": 0.9},
    "snippet": {"type": "string", "required": True},
    "source": {"type": "string", "required": False, "nullable": True},
    "rank": {"type": "integer", "required": True},
}


@pytest.mark.asyncio
async def test_web_search_scraping():
    results = await naver.scrape_web_search(query="파이썬", max_pages=3)

    # Validate each search result
    result_validator = Validator(SEARCH_WEB_SCHEMA)
    for result in results["results"]:
        validate_or_fail(result, result_validator)

    for k in SEARCH_WEB_SCHEMA:
        require_min_presence(results["results"], k, min_perc=SEARCH_WEB_SCHEMA[k].get("min_presence", 0.1))

    assert len(results["results"]) >= 5
