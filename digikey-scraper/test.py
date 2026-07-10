from cerberus import Validator as _Validator
import pytest
import digikey
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
    "name": {"type": "string"},
    "url": {"type": "string"},
    "digikey_part_number": {"type": "string"},
    "manufacturer_part_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "manufacturer": {"type": "string", "nullable": True, "min_presence": 0.1},
    "description": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
    "currency": {"type": "string", "nullable": True},
    "availability": {"type": "string", "nullable": True},
    "stock_quantity": {"type": "integer", "nullable": True},
    "image": {"type": "string", "nullable": True, "min_presence": 0.1},
    "specifications": {"type": "dict", "min_presence": 0.1},
}


category_result_schema = {
    "name": {"type": "string", "nullable": True, "min_presence": 0.1},
    "url": {"type": "string", "nullable": True, "min_presence": 0.1},
    "digikey_part_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "manufacturer_part_number": {"type": "string", "nullable": True, "min_presence": 0.1},
    "manufacturer": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
    "currency": {"type": "string", "nullable": True},
    "stock_quantity": {"type": "integer", "nullable": True},
    "availability": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True, "min_presence": 0.1},
}

keyword_result_schema = {
    "name": {"type": "string", "min_presence": 0.9},
    "url": {"type": "string", "min_presence": 0.9},
    "manufacturer": {"type": "string", "required": False, "min_presence": 0.1},
    "manufacturer_part_number": {"type": "string", "required": False, "min_presence": 0.0},
    "price": {"type": "string", "required": False, "min_presence": 0.0},
    "currency": {"type": "string", "required": False, "min_presence": 0.0},
    "stock_quantity": {"type": "integer", "required": False, "min_presence": 0.1},
    "image": {"type": "string", "required": False, "min_presence": 0.1},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    products = await digikey.scrape_products(
        urls=[
            "https://www.digikey.com/en/products/detail/adafruit-industries-llc/3111/6198256",
            "https://www.digikey.com/en/products/detail/phoenix-contact/2938235/2553505",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products:
        validate_or_fail(item, validator)
    for k in product_schema:
        require_min_presence(products, k, min_perc=product_schema[k].get("min_presence", 0.1))
    assert len(products) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_category_scraping():
    results = await digikey.scrape_category(
        url="https://www.digikey.com/en/products/filter/industrial-automation-accessories/800",
        max_pages=1,
    )
    validator = Validator(category_result_schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)
    for k in category_result_schema:
        require_min_presence(results, k, min_perc=category_result_schema[k].get("min_presence", 0.1))
    assert len(results) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    results = await digikey.scrape_search(keywords="resistor")
    validator = Validator(keyword_result_schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)
    for k in keyword_result_schema:
        require_min_presence(results, k, min_perc=keyword_result_schema[k].get("min_presence", 0.1))
    assert len(results) >= 5
