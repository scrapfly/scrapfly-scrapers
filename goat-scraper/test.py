import json
from pathlib import Path
from cerberus import Validator
import goat
import pytest
import pprint
import os

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
goat.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


product_schema = {
    "brandName": {"type": "string"},
    "color": {"type": "string"},
    "designer": {"type": "string"},
    "details": {"type": "string"},
    "forAuction": {"type": "boolean", "nullable": True},
    "id": {"type": "integer"},
    "internalShot": {"type": "string"},
    "maximumOfferCents": {"type": "integer"},
    "midsole": {"type": "string"},
    "minimumOfferCents": {"type": "integer"},
    "name": {"type": "string"},
    "productCategory": {"type": "string"},
    "productType": {"type": "string"},
    "silhouette": {"type": "string"},
    "sizeBrand": {"type": "string"},
    "sizeRange": {"type": "list", "schema": {"type": "float"}},
    "sizeBrand": {"type": "string"},
    "sku": {"type": "string"},
    "slug": {"type": "string"},
    "specialDisplayPriceCents": {"type": "integer"},
    "specialType": {"type": "string"},
    "status": {"type": "string"},
    "upperMaterial": {"type": "string"},
}

search_schema = {
    "id": {"type": "string"},
    "sku": {"type": "string"},
    "slug": {"type": "string"},
    "color": {"type": "string"},
    "category": {"type": "string"},
    "image_url": {"type": "string"},
    "product_type": {"type": "string"},
    "release_date": {"type": "integer"},
    "release_date_year": {"type": "integer"},
    "retail_price_cents": {"type": "integer"},
    "variation_id": {"type": "string"},
    "box_condition": {"type": "string"},
    "product_condition": {"type": "string"},
}


@pytest.mark.asyncio
async def test_product_scraping():
    result = await goat.scrape_products(
        urls=[
            "https://www.goat.com/sneakers/air-jordan-3-retro-white-cement-reimagined-dn3707-100",
            "https://www.goat.com/sneakers/travis-scott-x-air-jordan-1-retro-high-og-cd4487-100",
            "https://www.goat.com/sneakers/travis-scott-x-wmns-air-jordan-1-low-og-olive-dz4137-106",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/products.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
async def test_search_scraping():
    result = await goat.scrape_search("pumar dark", max_pages=3)
    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 3
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/search.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )
