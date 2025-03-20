import asyncio
import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest

import amazon
import pprint

pp = pprint.PrettyPrinter(indent=4)

amazon.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


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
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    urls = [
        "https://www.amazon.com/PlayStation%C2%AE5-console-slim-PlayStation-5/dp/B0CL61F39H",
        "https://www.amazon.com/Apple-2024-MacBook-13-inch-Laptop/dp/B0CX22ZW1T",
        "https://www.amazon.com/Atomic-Habits-Proven-Build-Break/dp/0735211299/",
        "https://www.amazon.com/42pcs-Fabric-Assorted-Squares-Nonwoven/dp/B01GCLS32M/",
    ]
    results = await asyncio.gather(*[amazon.scrape_product(url) for url in urls])
    results = [result for result_set in results for result in result_set]
    schema = {
        "name": {"type": "string"},
        "asin": {"type": "string"},
        "description": {"type": "string", "min_presence": 0.01},
        "stars": {"type": "string"},
        "rating_count": {"type": "string"},
        "style": {"type": "string", "nullable": True},
        "features": {"type": "list", "schema": {"type": "string"}},
        "images": {"type": "list", "schema": {"type": "string", "regex": "https://.*media-amazon.com.*"}},
        "info_table": {"type": "dict"},
    }
    validator = Validator(schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in schema:
        require_min_presence(results, k, min_perc=schema[k].get("min_presence", 0.1))
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/product.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    url = "https://www.amazon.com/s?k=kindle"
    result = await amazon.scrape_search(url, max_pages=2)
    assert len(result) >= 16  # the number can vary as search parser skips ads 
    schema = {
        "url": {"type": "string"},
        "title": {"type": "string"},
        "price": {"type": "string", "nullable": True},
        "real_price": {"type": "string", "nullable": True, "min_presence": 0.1},
        "rating": {"type": "float", "nullable": True, "min_presence": 0.2},
        "rating_count": {"type": "integer", "nullable": True, "min_presence": 0.2},
    }
    validator = Validator(schema, allow_unknown=True)
    for product in result:
        validate_or_fail(product, validator)
    for k in schema:
        require_min_presence(result, k, min_perc=schema[k].get("min_presence", 0.1))
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))



@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_review_scraping():
    url = "https://www.amazon.com/PlayStation%C2%AE5-console-slim-PlayStation-5/dp/B0CL61F39H"
    result = await amazon.scrape_reviews(url, max_pages=3)
    assert len(result) >= 8
    schema = {
        "text": {"type": "string"},
        "title": {"type": "string"},
        "location_and_date": {"type": "string"},
        "verified": {"type": "boolean"},
        "rating": {"type": "float"},
    }
    validator = Validator(schema, allow_unknown=True)
    for review in result:
        validate_or_fail(review, validator)
    for k in schema:
        require_min_presence(result, k, min_perc=schema[k].get("min_presence", 0.1))
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/reviews.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
