from cerberus import Validator
import pytest

import aliexpress
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
aliexpress.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
async def test_product_scraping():
    url = "https://www.aliexpress.com/item/4000927436411.html"
    result = await aliexpress.scrape_product(url)
    schema = {
        "name": {"type": "string"},
        "description_short": {"type": "string"},
        "images": {"type": "list", "schema": {"type": "string"}},
        "stock": {"type": "integer"},
        "variants": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "sku": {"type": "integer"},
                    "name": {"type": "string"},
                    "full_price": {"type": "float"},
                    "discount_price": {"type": "float"},
                },
            },
        },
        "seller": {
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "id": {"type": "integer"},
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
async def test_search_scraping():
    url = "https://www.aliexpress.com/wholesale?SearchText=drills"
    result = await aliexpress.scrape_search(url, max_pages=2)
    assert len(result) >= 100
    schema = {
        "id": {"type": "string"},
        "type": {"type": "string"},
        "thumbnail": {"type": "string"},
        "title": {"type": "string"},
        "currency": {"type": "string"},
        "price": {"type": "float"},
    }
    validator = Validator(schema, allow_unknown=True)
    for product in result:
        validate_or_fail(product, validator)


@pytest.mark.asyncio
async def test_review_scraping():
    result = await aliexpress.scrape_product_reviews("120565", "4000927436411", max_pages=2)
    assert len(result) > 10
    schema = {
        "text": {"type": "string"},
        "post_time": {"type": "string"},
        "stars": {"type": "float"},
        "user": {"type": "string", "nullable": True},
        "images": {"type": "list", "schema": {"type": "string"}},
    }
    validator = Validator(schema, allow_unknown=True)
    for review in result:
        validate_or_fail(review, validator)
