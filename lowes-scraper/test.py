from cerberus import Validator
import pytest
import lowes
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


product_schema = {
    "product_id": {"type": "string"},
    "item_number": {"type": "string", "nullable": True},
    "model_id": {"type": "string", "nullable": True},
    "url": {"type": "string"},
    "name": {"type": "string", "nullable": True},
    "brand": {"type": "string", "nullable": True},
    "price": {"type": "float", "nullable": True},
    "selling_price": {"type": "float", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "specifications": {"type": "dict"},
    "images": {"type": "list", "schema": {"type": "string"}},
    "store_number": {"type": "string", "nullable": True},
    "zip_code": {"type": "string", "nullable": True},
}

search_schema = {
    "product_id": {"type": "string"},
    "item_number": {"type": "string", "nullable": True},
    "model_id": {"type": "string", "nullable": True},
    "url": {"type": "string", "nullable": True},
    "name": {"type": "string", "nullable": True},
    "brand": {"type": "string", "nullable": True},
    "price": {"type": "float", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True},
}

store_location_schema = {
    "store_number": {"type": "string"},
    "name": {"type": "string", "nullable": True},
    "address": {"type": "string", "nullable": True},
    "city": {"type": "string", "nullable": True},
    "state": {"type": "string", "nullable": True},
    "zip_code": {"type": "string"},
    "phone": {"type": "string", "nullable": True},
    "distance": {"type": "float", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    products_data = await lowes.scrape_products(
        urls=[
            "https://www.lowes.com/pd/DEWALT-20-volt-Max-Brushless-Drill-1-Battery-Included-Charger-Included-and-Soft-Bag-included/5014148635",
            "https://www.lowes.com/pd/CRAFTSMAN-V20-20-volt-Max-1-2-in-Cordless-Drill-1-Battery-Included-and-Charger-Included/5004861567",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)
    assert len(products_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await lowes.scrape_search(query="cordless drill", max_pages=2)
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_store_locations_scraping():
    store_data = await lowes.scrape_store_locations(zip_code="28202")
    validator = Validator(store_location_schema, allow_unknown=True)
    for item in store_data:
        validate_or_fail(item, validator)
    assert len(store_data) >= 1
