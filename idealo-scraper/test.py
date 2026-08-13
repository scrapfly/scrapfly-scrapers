from cerberus import Validator
import pytest
import idealo
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


listing_schema = {
    "product_id": {"type": "string", "nullable": True},
    "name": {"type": "string", "nullable": True},
    "url": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True},
    "price": {"type": "number", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "offer_count": {"type": "integer", "nullable": True},
    "shop_name": {"type": "string", "nullable": True},
}

offer_schema = {
    "shop_name": {"type": "string", "nullable": True},
    "shop_url": {"type": "string", "nullable": True},
    "shop_rating": {"type": "string", "nullable": True},
    "shop_rating_count": {"type": "integer", "nullable": True},
    "price": {"type": "number", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "delivery_info": {"type": "string", "nullable": True},
    "merchant_name": {"type": "string", "nullable": True},
    "url": {"type": "string", "nullable": True},
}

product_schema = {
    "product_id": {"type": "string", "nullable": True},
    "name": {"type": "string", "nullable": True},
    "brand": {"type": "string", "nullable": True},
    "url": {"type": "string"},
    "image": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "rating": {"type": "number", "nullable": True},
    "rating_count": {"type": "integer", "nullable": True},
    "low_price": {"type": "number", "nullable": True},
    "high_price": {"type": "number", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "offer_count": {"type": "integer", "nullable": True},
    "offers": {
        "type": "list",
        "schema": {"type": "dict", "schema": offer_schema},
    },
}

manufacturer_schema = {
    "name": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "url": {"type": "string"},
    "result_count": {"type": "integer", "nullable": True},
    "products": {
        "type": "list",
        "schema": {"type": "dict", "schema": listing_schema},
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    data = await idealo.scrape_products(
        urls=["https://www.idealo.de/preisvergleich/OffersOfProduct/207644441.html"]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in data:
        validate_or_fail(item, validator)
    assert len(data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    data = await idealo.scrape_search(query="sonnenfinsternis brillen", max_pages=1)
    validator = Validator(listing_schema, allow_unknown=True)
    for item in data:
        validate_or_fail(item, validator)
    assert len(data) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_manufacturer_scraping():
    data = await idealo.scrape_manufacturer(
        url="https://www.idealo.de/preisvergleich/Hersteller/1274.html"
    )
    validator = Validator(manufacturer_schema, allow_unknown=True)
    validate_or_fail(data, validator)
    assert len(data["products"]) >= 5
