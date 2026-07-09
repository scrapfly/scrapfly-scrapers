import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import rs_online
import pprint

pp = pprint.PrettyPrinter(indent=4)

rs_online.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


product_schema = {
    "name": {"type": "string"},
    "url": {"type": "string"},
    "rs_stock_number": {"type": "string"},
    "mpn": {"type": "string", "nullable": True, "min_presence": 0.1},
    "brand": {"type": "string", "nullable": True, "min_presence": 0.1},
    "description": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
    "currency": {"type": "string", "nullable": True},
    "availability": {"type": "string", "nullable": True},
    "stock_quantity": {"type": "integer", "nullable": True},
    "image": {"type": "string", "nullable": True, "min_presence": 0.1},
    "specifications": {"type": "dict", "min_presence": 0.1},
    "compliance": {"type": "list"},
}


search_schema = {
    "name": {"type": "string", "nullable": True, "min_presence": 0.1},
    "url": {"type": "string", "nullable": True, "min_presence": 0.1},
    "rs_stock_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "mpn": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
    "currency": {"type": "string", "nullable": True},
    "availability": {"type": "string", "nullable": True},
    "stock_quantity": {"type": "integer", "nullable": True},
    "image": {"type": "string", "nullable": True, "min_presence": 0.1},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    products = await rs_online.scrape_products(
        urls=[
            "https://us.rs-online.com/product/aim-cambridge-cinch-connectivity-solutions/40-9715m/70081087/",
            "https://us.rs-online.com/product/cinch/dah15s/70152743/",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products:
        validate_or_fail(item, validator)
    for k in product_schema:
        require_min_presence(products, k, min_perc=product_schema[k].get("min_presence", 0.1))
    assert len(products) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / "results/products.json").write_text(
            json.dumps(products, indent=2, ensure_ascii=False)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_category_scraping():
    results = await rs_online.scrape_category(
        url="https://us.rs-online.com/connectors/d-sub-connectors-contacts-accessories/d-sub-connectors/",
        max_pages=1,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(results, k, min_perc=search_schema[k].get("min_presence", 0.1))
    assert len(results) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    results = await rs_online.scrape_search(query="resistor", max_pages=1)
    validator = Validator(search_schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(results, k, min_perc=search_schema[k].get("min_presence", 0.1))
    assert len(results) >= 5