from cerberus import Validator
import pytest
import nordstorm
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
nordstorm.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


product_schema = {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "type": {"type": "string"},
    "typeParent": {"type": "string"},
    "brand": {
        "type": "dict",
        "schema": {
            "brandName": {"type": "string"},
            "brandUrl": {"type": "string"},
            "hasBrandPage": {"type": "boolean"},
            "imsBrandId": {"type": "integer"},
        },
    },
    "description": {"type": "string"},
    "features": {"type": "list", "schema": {"type": "string"}},
    "gender": {"type": "string"},
    "media": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "colorCode": {"type": "string"},
                "colorName": {"type": "string"},
                "urls": {
                    "type": "list",
                    "schema": {"type": "string"}
                }
            }
        }
    },
    "variants": {
        "type": "dict",
        "valueschema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string"},
                "sizeId": {"type": "string"},
                "colorId": {"type": "string"},
                "totalQuantityAvailable": {"type": "integer"},
            },
        },
    },
}

search_schema = {
    "id": {"type": "integer"},
    "brandId": {"type": "integer"},
    "brandName": {"type": "string"},
    "styleNumber": {"type": "string"},
    "colorCount": {"type": "integer"},
    "colorDefaultId": {"type": "string"},
    "name": {"type": "string"},
    "extraNameCopy": {"type": "string"},
    "priceCurrencyCode": {"type": "string"},
    "priceCountryCode": {"type": "string"},
    "price": {
        "type": "dict",
        "schema": {
            "totalPriceRange": {
                "type": "dict",
                "schema": {
                    "min": {
                        "type": "dict",
                        "schema": {
                            "currencyCode": {"type": "string"},
                            "units": {"type": "integer"},
                            "nanos": {"type": "integer"},
                        },
                    },
                    "max": {
                        "type": "dict",
                        "schema": {
                            "currencyCode": {"type": "string"},
                            "units": {"type": "integer"},
                            "nanos": {"type": "integer"},
                        },
                    },
                },
            }
        },
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    products_data = await nordstorm.scrape_products(
        urls=[
            "https://www.nordstrom.com/s/nike-air-max-90-sneaker-men/6549520",
            "https://www.nordstrom.com/s/nike-sportswear-club-hoodie/6049642",
            "https://www.nordstrom.com/s/nike-phoenix-fleece-crewneck-sweatshirt/6665302",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)
    assert len(products_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await nordstorm.scrape_search(
        url="https://www.nordstrom.com/sr?origin=keywordsearch&keyword=indigo", max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 10
