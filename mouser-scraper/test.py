from cerberus import Validator as _Validator
import mouser
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

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
    "product_id": {"type": "string", "nullable": True},
    "manufacturer_part_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "manufacturer": {"type": "string", "min_presence": 0.1},
    "description": {"type": "string", "min_presence": 0.1},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
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

search_product_schema = {
    "product_id": {"type": "string", "nullable": True},
    "part_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "manufacturer_part_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "manufacturer": {"type": "string", "nullable": True, "min_presence": 0.1},
    "description": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
    "availability": {"type": "string", "nullable": True, "min_presence": 0.1},
    "url": {"type": "string"},
    "datasheet_url": {"type": "string", "nullable": True},
}

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    search_data = await mouser.scrape_search(query="Tool boxs")
    urls = [item["url"] for item in search_data["products"] if item.get("url")][:5]
    products_data = await mouser.scrape_product(urls=urls)
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)

    for k in product_schema:
        require_min_presence(products_data, k, min_perc=product_schema[k].get("min_presence", 0.1))

    assert len(products_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await mouser.scrape_search(query="Tool boxs")
    products_data = search_data["products"]
    validator = Validator(search_product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)

    for k in search_product_schema:
        require_min_presence(products_data, k, min_perc=search_product_schema[k].get("min_presence", 0.1))

    assert len(products_data) >= 10