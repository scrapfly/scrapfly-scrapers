"""Tests for Zoro.com scraper"""
import os
from cerberus import Validator as _Validator
import zoro
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
zoro.BASE_CONFIG["cache"] = True

# Custom Validator to support min_presence
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


# Schema for product data validation
product_schema = {
    "sku": {"type": "string"},
    "mpn": {"type": "string"},
    "name": {"type": "string"},
    "brand": {"type": "string", "min_presence": 0.8},
    "description": {"type": "string", "min_presence": 0.9},
    "price": {"type": "string"},
    "currency": {"type": "string"},
    "availability": {"type": "string"},
    "url": {"type": "string", "regex": r"https://www\.zoro\.com.*"},
    "specifications": {
        "type": "dict",
        "min_presence": 0.9,
        "valueschema": {"type": "string"},
    },
    "images": {
        "type": "list",
        "schema": {"type": "string", "regex": r"https://.*zoro\.com.*"},
    },
    "rating": {"type": "float", "nullable": True, "min_presence": 0.2},
    "review_count": {"type": "integer"},
    "reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "review_id": {"type": "integer", "required": True},
                "rating": {"type": "integer"},
                "headline": {"type": "string"},
                "comments": {"type": "string"},
                "nickname": {"type": "string"},
                "location": {"type": "string"},
                "created_date": {"type": "string"},
                "is_verified_buyer": {"type": "boolean"},
                "helpful_votes": {"type": "integer"},
                "media_count": {"type": "integer"},
            },
        },
    },
}

# Schema for search listing product (from API)
search_product_schema = {
    "title": {"type": "string", "required": True},
    "brand": {"type": "string", "nullable": True, "min_presence": 0.7},
    "price": {"type": "float", "nullable": True, "min_presence": 0.9},
    "zoroNo": {"type": "string", "required": True},
    "mfrNo": {"type": "string", "nullable": True, "min_presence": 0.8},
    "slug": {"type": "string", "required": True},
    "attributes": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "value": {"type": "string"},
                "normalizedValue": {"type": "string", "nullable": True},
                "rank": {"type": "integer", "nullable": True},
            },
        },
    },
    "media": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "type": {"type": "string"},
            },
        },
    },
    "salesStatus": {"type": "string", "nullable": True},
    "isDiscontinued": {"type": "boolean", "nullable": True, "min_presence": 0.0},
    "leadTime": {"type": "integer", "nullable": True},
}

# Schema for search listing data validation
search_listing_schema = {
    "total_pages": {"type": "integer", "required": True},
    "total_results": {"type": "integer", "required": True},
    "products": {
        "type": "list",
        "schema": {"type": "dict", "schema": search_product_schema},
    },
}

@pytest.mark.asyncio
async def test_product_scraping():
    products_data = await zoro.scrape_product(
        urls=[
        "https://www.zoro.com/proto-general-purpose-double-latch-tool-box-with-tray-steel-red-20-w-x-85-d-x-95-h-j9975r/i/G0067825/",
        "https://www.zoro.com/stanley-series-2000-tool-box-plastic-blackyellow-19-in-w-x-10-14-in-d-x-10-in-h-019151m/i/G6197466/",
        "https://www.zoro.com/ansell-hyflex-coated-gloves-polyurethane-dipped-palm-coated-ansi-abrasion-level-3-black-large-1-pair-48-101/i/G0050565/"
        ]
    )

    # Validate the product structure
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)

    # Check field presence
    for k in product_schema:
        require_min_presence(products_data, k, min_perc=product_schema[k].get("min_presence", 0.1))

    assert len(products_data) >= 1

@pytest.mark.asyncio
async def test_search_scraping():
    search_listing_data = await zoro.scrape_search_listing("Gloves", max_pages=3)
    
    # Validate the search listing structure
    validator = Validator(search_listing_schema, allow_unknown=True)
    validate_or_fail(search_listing_data, validator)
    
    # Validate products separately
    products = search_listing_data.get("products", [])
    product_validator = Validator(search_product_schema, allow_unknown=True)
    for product in products:
        validate_or_fail(product, product_validator)
    
    # Check field presence for products
    for k in search_product_schema:
        require_min_presence(products, k, min_perc=search_product_schema[k].get("min_presence", 0.1))
    
    assert len(products) >= 20