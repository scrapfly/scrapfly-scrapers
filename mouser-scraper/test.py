"""Tests for Mouser.com scraper"""
from cerberus import Validator as _Validator
import mouser
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
mouser.BASE_CONFIG["cache"] = True

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
    "product_id": {"type": "string", "nullable": True},
    "part_number": {"type": "string", "min_presence": 0.9},
    "manufacturer_part_number": {"type": "string", "nullable": True, "min_presence": 0.8},
    "manufacturer": {"type": "string", "min_presence": 0.9},
    "description": {"type": "string", "min_presence": 0.9},
    "price": {"type": "string", "nullable": True, "min_presence": 0.8},
    "currency": {"type": "string"},
    "availability": {"type": "string", "nullable": True},
    "stock_quantity": {"type": "integer", "nullable": True},
    "images": {
        "type": "list",
        "schema": {"type": "string"},
    },
    "specifications": {
        "type": "dict",
        "valueschema": {"type": "string"},
    },
    "datasheet_url": {"type": "string", "nullable": True},
    "url": {"type": "string"},
}

# Schema for search listing product
search_product_schema = {
    "product_id": {"type": "string", "nullable": True},
    "part_number": {"type": "string", "nullable": True, "min_presence": 0.9},
    "manufacturer_part_number": {"type": "string", "nullable": True, "min_presence": 0.8},
    "manufacturer": {"type": "string", "nullable": True, "min_presence": 0.8},
    "description": {"type": "string", "nullable": True, "min_presence": 0.8},
    "price": {"type": "string", "nullable": True, "min_presence": 0.7},
    "availability": {"type": "string", "nullable": True, "min_presence": 0.7},
    "url": {"type": "string"},
    "datasheet_url": {"type": "string", "nullable": True},
}
@pytest.mark.asyncio
async def test_product_scraping():
    products_data = await mouser.scrape_product(
        urls=[
            "https://www.mouser.com/ProductDetail/BusBoard-Prototype-Systems/BOX3-1455N-BK?qs=I13xAFqYpRSd61TQKf31Yw%3D%3D",
            "https://www.mouser.com/ProductDetail/Olimex-Ltd/BOX-ESP32-GATEWAY-F?qs=%252BXxaIXUDbq2PKdoOW6%252BSdA%3D%3D",
            "https://www.mouser.com/ProductDetail/Olimex-Ltd/BOX-ESP32-GATEWAY-EA?qs=Rp5uXu7WBW8AcjUyETTTSg%3D%3D"
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)

    for k in product_schema:
        require_min_presence(products_data, k, min_perc=product_schema[k].get("min_presence", 0.1))

    assert len(products_data) >= 1

@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await mouser.scrape_search(query="Tool boxs")
    products_data = search_data["products"]
    validator = Validator(search_product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)

    for k in search_product_schema:
        require_min_presence(products_data, k, min_perc=search_product_schema[k].get("min_presence", 0.1))

    assert len(products_data) >= 10