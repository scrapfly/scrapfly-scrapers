import json
import os
from pathlib import Path
from cerberus import Validator
import fashionphile
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
fashionphile.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


product_schema = {
    "id": {"type": "integer"},
    "sku": {"type": "string"},
    "title": {"type": "string"},
    "slug": {"type": "string"},
    "price": {"type": "integer"},
    "renewDays": {"type": "integer"},
    "discountedPrice": {"type": "integer"},
    "discountEnabled": {"type": "integer"},
    "discountedTier": {"type": "integer"},
    "madeAvailableAt": {"type": "string"},
    "approvedAt": {"type": "string"},
    "madeAvailableAtUTC": {"type": "string"},
    "year": {"type": "integer", "nullable": True},
    "condition": {"type": "string"},
    "authenticCta": {"type": "string"},
    "brand": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "slug": {"type": "string"},
                "type": {"type": "string"},
                "description": {"type": "string"},
                "title": {"type": "string"},
            },
        },
    },
}

search_schema = {
    "brands": {"type": "string"},
    "product_name": {"type": "string"},
    "condition": {"type": "string"},
    "discounted_price": {"type": "integer"},
    "price": {"type": "integer"},
    "id": {"type": "integer"},
}


@pytest.mark.asyncio
async def test_product_scraping():
    products_data = await fashionphile.scrape_products(
        urls=[
            "https://www.fashionphile.com/p/bottega-veneta-nappa-twisted-padded-intrecciato-curve-slide-sandals-36-black-1048096",
            "https://www.fashionphile.com/p/louis-vuitton-ostrich-lizard-majestueux-tote-mm-navy-1247825",
            "https://www.fashionphile.com/p/louis-vuitton-monogram-multicolor-lodge-gm-black-1242632",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)
    assert len(products_data) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        products_data.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/products.json').write_text(json.dumps(products_data, indent=2, ensure_ascii=False, default=str))


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await fashionphile.scrape_search(
        url="https://www.fashionphile.com/shop/discounted/all", max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) == 360
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        search_data.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(search_data, indent=2, ensure_ascii=False, default=str))
